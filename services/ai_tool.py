import logging
import os
from ..policy import config
from comprehensive_eval_pro.utils.http_client import create_session, request_json_response

logger = logging.getLogger("AITool")


class _AIProvider:
    def __init__(self, *, name: str, api_key: str, base_url: str):
        self.name = name
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").rstrip("/")
        self.session = create_session(retries=0)

    def enabled(self) -> bool:
        return bool(self.api_key) and bool(self.base_url)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict],
        max_tokens: int = 256,
        temperature: float = 0.7,
        timeout: int = 60,
    ) -> str:
        if not self.enabled():
            return ""

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            res_data, response = request_json_response(
                self.session,
                "POST",
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
                logger=logger,
            )
            if response is None or response.status_code != 200 or (not isinstance(res_data, dict)):
                logger.error(f"AI 响应错误({self.name}): {res_data}")
                return ""

            choices = res_data.get("choices") or []
            content = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
            return content
        except Exception as e:
            logger.error(f"AI 请求异常({self.name}): {e}")
            return ""


class AIModelTool:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.providers: dict[str, _AIProvider] = {}

        # 1. 默认提供者 (优先传参，其次配置/环境变量)
        default_api_key = (api_key or config.get_setting("siliconflow_api_key", "", env_name="SILICONFLOW_API_KEY")).strip()
        default_base_url = (base_url or config.get_setting("ai_base_url", "https://api.siliconflow.cn/v1", env_name="CEP_AI_BASE_URL")).strip()

        if default_api_key:
            self.providers["default"] = _AIProvider(
                name="default",
                api_key=default_api_key,
                base_url=default_base_url,
            )
            self.providers.setdefault(
                "siliconflow",
                _AIProvider(name="siliconflow", api_key=default_api_key, base_url=default_base_url),
            )

        # 2. 多提供者支持 (CEP_AI_PROVIDERS)
        provider_names_str = config.get_setting("ai_providers", "", env_name="CEP_AI_PROVIDERS")
        names = [x.strip() for x in provider_names_str.split(",") if x.strip()]
        for name in names:
            key = config.get_setting(f"ai_{name.lower()}_api_key", "", env_name=f"CEP_AI_{name.upper()}_API_KEY").strip()
            url = config.get_setting(f"ai_{name.lower()}_base_url", "", env_name=f"CEP_AI_{name.upper()}_BASE_URL").strip()
            if key and url:
                self.providers[name.lower()] = _AIProvider(name=name.lower(), api_key=key, base_url=url)

        # 3. 默认选中的提供者
        self.default_provider = config.get_setting("ai_provider_default", "", env_name="CEP_AI_PROVIDER_DEFAULT").strip().lower() or (
            "default" if "default" in self.providers else "siliconflow"
        )

    def enabled(self) -> bool:
        p = self.providers.get(self.default_provider)
        return bool(p and p.enabled())

    def _resolve(self, model_spec: str) -> tuple[_AIProvider | None, str]:
        spec = (model_spec or "").strip()
        if not spec:
            return None, ""

        provider_key = ""
        model = spec

        if "::" in spec:
            provider_key, model = spec.split("::", 1)
        elif ":" in spec:
            maybe_provider, maybe_model = spec.split(":", 1)
            if maybe_provider.lower() in self.providers:
                provider_key, model = maybe_provider, maybe_model

        provider_key = (provider_key or self.default_provider).strip().lower()
        provider = self.providers.get(provider_key)
        return provider, (model or "").strip()

    def chat(
        self,
        *,
        model: str,
        messages: list[dict],
        max_tokens: int = 256,
        temperature: float = 0.7,
        timeout: int = 60,
    ) -> str:
        provider, model_name = self._resolve(model)
        if not provider or not provider.enabled() or (not model_name):
            return ""
        return provider.chat(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
