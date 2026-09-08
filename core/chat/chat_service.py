import base64
from pathlib import Path
from typing import Any, Callable, ClassVar, Iterator, Sequence

from ai_models_manager.core.chat.models.chat_message_data_model import ChatMessageDataModel
from ai_models_manager.core.ollama.models.ollama_chat_chunk_data_model import OllamaChatChunkDataModel
from ai_models_manager.core.ollama.models.ollama_chat_response_data_model import OllamaChatResponseDataModel
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.session.models.chat_session_data_model import ChatSessionDataModel
from ai_models_manager.core.storage.session_storage import SessionStorage
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class ChatService:
    """Run durable Ollama chat turns backed by session packages."""

    BACKEND_OLLAMA: ClassVar[str] = "ollama"

    def __init__(
        self,
        ollama: OllamaBackend,
        session_storage: SessionStorage,
        warning: Callable[[str], None] | None = None,
    ) -> None:
        self.ollama = ollama
        self.session_storage = session_storage
        self.warning = warning or (lambda message: None)

    def send_message(
        self,
        session_id: str,
        content: str,
        attachments: Sequence[Path] = (),
    ) -> OllamaChatResponseDataModel:
        session = self.session_storage.load(session_id)
        if not isinstance(session, ChatSessionDataModel):
            raise ValueError("Chat messages require a chat session.")
        self._prune_missing_attachments(session)
        if session.backend != self.BACKEND_OLLAMA:
            raise ValueError(
                f"Unsupported chat session backend: {session.backend}"
            )
        if not content.strip() and not attachments:
            raise ValueError("Chat message cannot be empty.")

        api_messages = [
            self._api_message(session_id, message)
            for message in session.messages
        ]
        pending_message: dict[str, Any] = {
            "role": "user",
            "content": content,
        }
        pending_images = [self._encode_image(path) for path in attachments]
        if pending_images:
            pending_message["images"] = pending_images
        api_messages.append(pending_message)

        response = self.ollama.chat(
            model=session.model,
            messages=api_messages,
            context_length=session.context_length,
        )

        stored_attachments = tuple(
            self.session_storage.add_attachment(session_id, path)
            for path in attachments
        )
        session.messages.extend(
            (
                ChatMessageDataModel(
                    role="user",
                    content=content,
                    attachments=stored_attachments,
                ),
                ChatMessageDataModel(
                    role="assistant",
                    content=response.content,
                ),
            )
        )
        self.session_storage.save(session)
        return response

    def send_ephemeral_message(
        self,
        model: str,
        history: list[dict[str, Any]],
        content: str,
        *,
        context_length: int | None = None,
        attachments: Sequence[Path] = (),
    ) -> OllamaChatResponseDataModel:
        if not content.strip() and not attachments:
            raise ValueError("Chat message cannot be empty.")
        user_message: dict[str, Any] = {
            "role": "user",
            "content": content,
        }
        images = [self._encode_image(path) for path in attachments]
        if images:
            user_message["images"] = images
        response = self.ollama.chat(
            model=model,
            messages=[*history, user_message],
            context_length=context_length,
        )
        history.extend(
            (
                user_message,
                {"role": "assistant", "content": response.content},
            )
        )
        return response

    def stream_ephemeral_message(
        self,
        model: str,
        history: list[dict[str, Any]],
        content: str,
        *,
        context_length: int | None = None,
        attachments: Sequence[Path] = (),
    ) -> Iterator[OllamaChatChunkDataModel]:
        if not content.strip() and not attachments:
            raise ValueError("Chat message cannot be empty.")
        user_message: dict[str, Any] = {
            "role": "user",
            "content": content,
        }
        images = [self._encode_image(path) for path in attachments]
        if images:
            user_message["images"] = images
        response_content: list[str] = []
        for chunk in self.ollama.chat_stream(
            model=model,
            messages=[*history, user_message],
            context_length=context_length,
        ):
            response_content.append(chunk.content)
            if chunk.done:
                yield chunk
                history.extend(
                    (
                        user_message,
                        {
                            "role": "assistant",
                            "content": "".join(response_content),
                        },
                    )
                )
                return
            yield chunk
        raise OllamaBackendError(
            "Ollama ended the chat stream before the final chunk."
        )

    def stream_message(
        self,
        session_id: str,
        content: str,
        attachments: Sequence[Path] = (),
    ) -> Iterator[OllamaChatChunkDataModel]:
        session = self.session_storage.load(session_id)
        if not isinstance(session, ChatSessionDataModel):
            raise ValueError("Chat messages require a chat session.")
        self._prune_missing_attachments(session)
        if session.backend != self.BACKEND_OLLAMA:
            raise ValueError(
                f"Unsupported chat session backend: {session.backend}"
            )
        if not content.strip() and not attachments:
            raise ValueError("Chat message cannot be empty.")
        api_messages = [
            self._api_message(session_id, message)
            for message in session.messages
        ]
        pending_message: dict[str, Any] = {
            "role": "user",
            "content": content,
        }
        pending_images = [self._encode_image(path) for path in attachments]
        if pending_images:
            pending_message["images"] = pending_images
        response_content: list[str] = []
        for chunk in self.ollama.chat_stream(
            model=session.model,
            messages=[*api_messages, pending_message],
            context_length=session.context_length,
        ):
            response_content.append(chunk.content)
            if chunk.done:
                yield chunk
                stored_attachments = tuple(
                    self.session_storage.add_attachment(session_id, path)
                    for path in attachments
                )
                session.messages.extend(
                    (
                        ChatMessageDataModel(
                            role="user",
                            content=content,
                            attachments=stored_attachments,
                        ),
                        ChatMessageDataModel(
                            role="assistant",
                            content="".join(response_content),
                        ),
                    )
                )
                self.session_storage.save(session)
                return
            yield chunk
        raise OllamaBackendError(
            "Ollama ended the chat stream before the final chunk."
        )

    def _api_message(
        self,
        session_id: str,
        message: ChatMessageDataModel,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        images = [
            self._encode_image(
                self.session_storage.attachment_path(
                    session_id, relative_path
                )
            )
            for relative_path in message.attachments
        ]
        if images:
            data["images"] = images
        return data

    def _prune_missing_attachments(
        self,
        session: ChatSessionDataModel,
    ) -> None:
        changed = False
        messages: list[ChatMessageDataModel] = []
        for message in session.messages:
            available: list[str] = []
            for relative_path in message.attachments:
                path = self.session_storage.attachment_path(
                    session.session_id, relative_path
                )
                if path.is_file():
                    available.append(relative_path)
                else:
                    changed = True
                    self.warning(
                        "Saved chat attachment is missing and will be "
                        f"removed from the session: {relative_path}"
                    )
            messages.append(
                ChatMessageDataModel(
                    role=message.role,
                    content=message.content,
                    attachments=tuple(available),
                )
            )
        if changed:
            session.messages = messages
            self.session_storage.save(session)

    @staticmethod
    def _encode_image(path: Path) -> str:
        path = path.expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Chat attachment not found: {path}")
        return base64.b64encode(path.read_bytes()).decode("ascii")
