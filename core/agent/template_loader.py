# core/agent/template_loader.py
"""提示词模板加载器。

两层覆盖策略：
1. 内置模板：resources/prompts/<agent_type>.default.yaml
2. 沙盒覆盖：<user_data>/prompts/<agent_type>.yaml（优先）

模板格式（YAML）：
    version: 1
    model: null
    system_prompt: "You are..."
    user_prompt_template: "Article: {{ content }}\n\nTask: {{ task }}"
    config:
      temperature: 0.7
      max_tokens: 2048
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import Template


@dataclass
class PromptTemplate:
    agent_type: str  # "summary" | "translation" | "tagging"
    version: int
    system_prompt: str
    user_prompt_template: str
    config: dict
    source: str  # "builtin" | "sandbox"


class TemplateLoader:
    """提示词模板加载器。

    Usage:
        loader = TemplateLoader(builtin_dir="resources/prompts",
                                sandbox_dir="~/.mercury/prompts")
        tpl = loader.load("summary")
        system, user = loader.render(tpl, content="...", task="summarize")
    """

    def __init__(self, builtin_dir: str, sandbox_dir: str) -> None:
        self._builtin = Path(builtin_dir)
        self._sandbox = Path(sandbox_dir).expanduser().resolve()

    def load(self, agent_type: str) -> PromptTemplate:
        """加载指定 Agent 类型的提示词模板。沙盒覆盖优先。"""
        sandbox_file = self._sandbox / f"{agent_type}.yaml"
        builtin_file = self._builtin / f"{agent_type}.default.yaml"

        if sandbox_file.exists():
            return self._parse(agent_type, sandbox_file, "sandbox")
        if builtin_file.exists():
            return self._parse(agent_type, builtin_file, "builtin")
        raise FileNotFoundError(
            f"No template found for agent_type={agent_type}"
        )

    def init_sandbox(self, agent_type: str) -> Path:
        """首次自定义：从内置复制到沙盒，不覆盖已有文件。"""
        self._sandbox.mkdir(parents=True, exist_ok=True)
        sandbox_file = self._sandbox / f"{agent_type}.yaml"
        builtin_file = self._builtin / f"{agent_type}.default.yaml"

        if not sandbox_file.exists() and builtin_file.exists():
            shutil.copy2(builtin_file, sandbox_file)
        return sandbox_file

    def reset_to_builtin(self, agent_type: str) -> None:
        """删除沙盒覆盖，回退到内置模板。"""
        sandbox_file = self._sandbox / f"{agent_type}.yaml"
        if sandbox_file.exists():
            sandbox_file.unlink()

    def _parse(
        self, agent_type: str, filepath: Path, source: str
    ) -> PromptTemplate:
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return PromptTemplate(
            agent_type=agent_type,
            version=data.get("version", 1),
            system_prompt=data.get("system_prompt", ""),
            user_prompt_template=data.get("user_prompt_template", ""),
            config=data.get("config", {}),
            source=source,
        )

    def render(
        self, tpl: PromptTemplate, **variables
    ) -> tuple[str, str]:
        """渲染提示词，返回 (system_prompt, user_prompt)。"""
        jinja = Template(tpl.user_prompt_template)
        return tpl.system_prompt, jinja.render(**variables)
