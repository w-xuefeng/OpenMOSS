"""
配置态 Agent Service

当前阶段先把数据模型和 API 语义切到最新设计，同时保留对旧字段输入的兼容映射。
"""
import json
import os
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.managed_agent import (
    ManagedAgent,
    ManagedAgentCommBinding,
    ManagedAgentHostConfig,
    ManagedAgentNotificationChannel,
    ManagedAgentPromptAsset,
    ManagedAgentSchedule,
)


def _generate_slug(name: str) -> str:
    """从名称生成 slug。"""
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff-]", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = str(uuid.uuid4())[:8]
    return slug


def _bump_config_version(db: Session, managed_agent: ManagedAgent) -> None:
    """递增配置版本。"""
    managed_agent.config_version = (managed_agent.config_version or 0) + 1
    managed_agent.updated_at = datetime.now()
    db.flush()


def _mask(value: Optional[str]) -> Optional[str]:
    """简单脱敏。"""
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-2:]}"


def _default_render_strategy(host_platform: str, deployment_mode: str) -> str:
    """根据宿主平台和部署模式给出默认渲染策略。"""
    if host_platform == "openclaw":
        if deployment_mode == "bind_main_agent":
            return "openclaw_inline_schedule"
        return "openclaw_workspace_files"
    return "host_default"


def _legacy_identity_to_content(
    identity_content: Optional[str] = None,
    identity_name: Optional[str] = None,
    identity_emoji: Optional[str] = None,
    identity_theme: Optional[str] = None,
) -> Optional[str]:
    """把旧的 identity 字段组合成统一文本。"""
    if identity_content is not None:
        return identity_content

    if not any([identity_name, identity_emoji, identity_theme]):
        return None

    lines = ["# IDENTITY.md - Who Am I?", ""]
    if identity_name:
        lines.append(f"- Name: {identity_name}")
    if identity_emoji:
        lines.append(f"- Emoji: {identity_emoji}")
    if identity_theme:
        lines.append(f"- Theme: {identity_theme}")
    return "\n".join(lines)


def _legacy_prompt_mode_to_strategy(prompt_delivery_mode: Optional[str]) -> Optional[str]:
    """兼容旧的 prompt_delivery_mode。"""
    if prompt_delivery_mode == "embed_in_cron":
        return "openclaw_inline_schedule"
    if prompt_delivery_mode == "write_agents_md":
        return "openclaw_workspace_files"
    return None


def _ensure_host_config(db: Session, agent: ManagedAgent) -> ManagedAgentHostConfig:
    """确保宿主配置记录存在。"""
    host_config = db.query(ManagedAgentHostConfig).filter(
        ManagedAgentHostConfig.managed_agent_id == agent.id
    ).first()
    if host_config:
        return host_config

    host_config = ManagedAgentHostConfig(
        id=str(uuid.uuid4()),
        managed_agent_id=agent.id,
        host_platform=agent.host_platform,
    )
    db.add(host_config)
    db.flush()
    return host_config


def _ensure_prompt_asset(db: Session, agent: ManagedAgent) -> ManagedAgentPromptAsset:
    """确保 Prompt 资产记录存在。"""
    prompt_asset = db.query(ManagedAgentPromptAsset).filter(
        ManagedAgentPromptAsset.managed_agent_id == agent.id
    ).first()
    if prompt_asset:
        return prompt_asset

    prompt_asset = ManagedAgentPromptAsset(
        id=str(uuid.uuid4()),
        managed_agent_id=agent.id,
        template_role=agent.role,
        host_render_strategy=_default_render_strategy(agent.host_platform, agent.deployment_mode),
        authority_source="database",
    )
    db.add(prompt_asset)
    db.flush()
    return prompt_asset


def _normalize_host_config_kwargs(kwargs: Dict[str, object]) -> Dict[str, object]:
    """兼容旧 host config 字段名。"""
    data = dict(kwargs)
    if not data.get("host_agent_identifier") and data.get("openclaw_agent_id"):
        data["host_agent_identifier"] = data["openclaw_agent_id"]
    if not data.get("workdir_path") and data.get("workspace_path"):
        data["workdir_path"] = data["workspace_path"]
    if not data.get("default_model") and data.get("model"):
        data["default_model"] = data["model"]
    if data.get("host_config_payload") is not None:
        data["host_config_payload_encrypted"] = data["host_config_payload"]
    return {
        key: value for key, value in data.items()
        if key in {
            "host_agent_identifier",
            "workdir_path",
            "default_model",
            "host_config_payload_encrypted",
            "host_metadata_json",
        }
    }


def _normalize_prompt_asset_kwargs(kwargs: Dict[str, object]) -> Dict[str, object]:
    """兼容旧 Prompt 字段名。"""
    data = dict(kwargs)

    if data.get("agents_md_content") is not None and data.get("system_prompt_content") is None:
        data["system_prompt_content"] = data["agents_md_content"]
    if data.get("soul_md_content") is not None and data.get("persona_prompt_content") is None:
        data["persona_prompt_content"] = data["soul_md_content"]

    identity_content = _legacy_identity_to_content(
        identity_content=data.get("identity_content"),
        identity_name=data.get("identity_name"),
        identity_emoji=data.get("identity_emoji"),
        identity_theme=data.get("identity_theme"),
    )
    if identity_content is not None:
        data["identity_content"] = identity_content

    if data.get("host_render_strategy") is None:
        strategy = _legacy_prompt_mode_to_strategy(data.get("prompt_delivery_mode"))
        if strategy:
            data["host_render_strategy"] = strategy

    return {
        key: value for key, value in data.items()
        if key in {
            "system_prompt_content",
            "persona_prompt_content",
            "identity_content",
            "host_render_strategy",
            "notes",
        }
    }


def _normalize_schedule_kwargs(
    kwargs: Dict[str, object],
    existing_execution_options_json: Optional[str] = None,
) -> Dict[str, object]:
    """兼容旧 Schedule 字段名。"""
    data = dict(kwargs)

    if data.get("every") and not data.get("schedule_expr"):
        data["schedule_expr"] = data["every"]

    if data.get("cron_message_content") is not None and data.get("schedule_message_content") is None:
        data["schedule_message_content"] = data["cron_message_content"]

    if data.get("schedule_type") is None:
        data["schedule_type"] = "interval"

    execution_options = {}
    if existing_execution_options_json:
        try:
            execution_options = json.loads(existing_execution_options_json)
        except Exception:
            execution_options = {}

    if data.get("execution_options_json"):
        try:
            execution_options.update(json.loads(str(data["execution_options_json"])))
        except Exception:
            execution_options = {"raw": data["execution_options_json"]}

    if data.get("thinking_mode") is not None:
        execution_options["thinking_mode"] = data["thinking_mode"]
    if data.get("announce") is not None:
        execution_options["announce"] = data["announce"]
    if data.get("session_mode") is not None:
        execution_options["session_mode"] = data["session_mode"]

    if execution_options:
        data["execution_options_json"] = json.dumps(execution_options, ensure_ascii=False)

    return {
        key: value for key, value in data.items()
        if key in {
            "name",
            "enabled",
            "schedule_type",
            "schedule_expr",
            "timeout_seconds",
            "model_override",
            "execution_options_json",
            "schedule_message_content",
        }
    }


def _normalize_comm_binding_kwargs(kwargs: Dict[str, object]) -> Dict[str, object]:
    """兼容旧平台绑定字段名。"""
    data = dict(kwargs)
    if not data.get("provider") and data.get("platform"):
        data["provider"] = data["platform"]
    if not data.get("binding_key") and data.get("account_id"):
        data["binding_key"] = data["account_id"]
    if data.get("routing_policy") is not None and data.get("routing_policy_json") is None:
        data["routing_policy_json"] = data["routing_policy"]
    if data.get("secret_payload") is not None and data.get("config_payload") is None:
        data["config_payload"] = data["secret_payload"]
    if data.get("config_payload") is not None:
        data["config_payload_encrypted"] = data["config_payload"]

    return {
        key: value for key, value in data.items()
        if key in {
            "provider",
            "binding_key",
            "display_name",
            "enabled",
            "routing_policy_json",
            "metadata_json",
            "config_payload_encrypted",
        }
    }


def create_managed_agent(
    db: Session,
    name: str,
    slug: str,
    role: str,
    deployment_mode: str,
    description: str = "",
    host_platform: str = "openclaw",
    host_access_mode: str = "local",
    host_agent_identifier: Optional[str] = None,
    workdir_path: Optional[str] = None,
    default_model: Optional[str] = None,
) -> ManagedAgent:
    """创建配置态 Agent。"""
    existing = db.query(ManagedAgent).filter(ManagedAgent.slug == slug).first()
    if existing:
        raise ValueError(f"slug '{slug}' 已被使用")

    agent = ManagedAgent(
        id=str(uuid.uuid4()),
        name=name,
        slug=slug,
        role=role,
        description=description,
        host_platform=host_platform,
        deployment_mode=deployment_mode,
        host_access_mode=host_access_mode,
        status="draft",
        config_version=1,
    )
    db.add(agent)
    db.flush()

    host_config = ManagedAgentHostConfig(
        id=str(uuid.uuid4()),
        managed_agent_id=agent.id,
        host_platform=host_platform,
        host_agent_identifier=host_agent_identifier,
        workdir_path=workdir_path,
        default_model=default_model,
    )
    db.add(host_config)

    prompt_asset = ManagedAgentPromptAsset(
        id=str(uuid.uuid4()),
        managed_agent_id=agent.id,
        template_role=role,
        host_render_strategy=_default_render_strategy(host_platform, deployment_mode),
        authority_source="database",
    )
    db.add(prompt_asset)

    db.commit()
    db.refresh(agent)
    return agent


def get_managed_agent(db: Session, agent_id: str) -> Optional[ManagedAgent]:
    """获取单个配置态 Agent。"""
    return db.query(ManagedAgent).filter(ManagedAgent.id == agent_id).first()


def get_managed_agent_or_404(db: Session, agent_id: str) -> ManagedAgent:
    """获取配置态 Agent，不存在则抛异常。"""
    agent = get_managed_agent(db, agent_id)
    if not agent:
        raise ValueError(f"配置态 Agent 不存在: {agent_id}")
    return agent


def list_managed_agents(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    role: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[ManagedAgent], int]:
    """分页查询配置态 Agent。"""
    query = db.query(ManagedAgent)
    if role:
        query = query.filter(ManagedAgent.role == role)
    if status:
        query = query.filter(ManagedAgent.status == status)

    total = query.count()
    items = (
        query.order_by(ManagedAgent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def update_managed_agent(db: Session, agent_id: str, **kwargs) -> ManagedAgent:
    """更新配置态 Agent 基础信息。"""
    agent = get_managed_agent_or_404(db, agent_id)
    changed = False

    for key, value in kwargs.items():
        if value is not None and hasattr(agent, key) and getattr(agent, key) != value:
            setattr(agent, key, value)
            changed = True

    if changed:
        _bump_config_version(db, agent)

        host_config = db.query(ManagedAgentHostConfig).filter(
            ManagedAgentHostConfig.managed_agent_id == agent.id
        ).first()
        if host_config and host_config.host_platform != agent.host_platform:
            host_config.host_platform = agent.host_platform

    db.commit()
    db.refresh(agent)
    return agent


def delete_managed_agent(db: Session, agent_id: str) -> None:
    """硬删除配置态 Agent 及其关联数据。"""
    agent = get_managed_agent_or_404(db, agent_id)

    db.query(ManagedAgentHostConfig).filter(
        ManagedAgentHostConfig.managed_agent_id == agent_id
    ).delete()
    db.query(ManagedAgentPromptAsset).filter(
        ManagedAgentPromptAsset.managed_agent_id == agent_id
    ).delete()
    db.query(ManagedAgentSchedule).filter(
        ManagedAgentSchedule.managed_agent_id == agent_id
    ).delete()
    db.query(ManagedAgentCommBinding).filter(
        ManagedAgentCommBinding.managed_agent_id == agent_id
    ).delete()
    db.query(ManagedAgentNotificationChannel).filter(
        ManagedAgentNotificationChannel.managed_agent_id == agent_id
    ).delete()

    db.delete(agent)
    db.commit()


def get_host_config(db: Session, managed_agent_id: str) -> Optional[ManagedAgentHostConfig]:
    """获取宿主平台配置。"""
    return db.query(ManagedAgentHostConfig).filter(
        ManagedAgentHostConfig.managed_agent_id == managed_agent_id
    ).first()


def update_host_config(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentHostConfig:
    """更新宿主平台配置。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    host_config = _ensure_host_config(db, agent)
    normalized = _normalize_host_config_kwargs(kwargs)

    changed = False
    for key, value in normalized.items():
        if value is not None and hasattr(host_config, key) and getattr(host_config, key) != value:
            setattr(host_config, key, value)
            changed = True

    if host_config.host_platform != agent.host_platform:
        host_config.host_platform = agent.host_platform
        changed = True

    if changed:
        host_config.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(host_config)
    return host_config


def get_prompt_asset(db: Session, managed_agent_id: str) -> Optional[ManagedAgentPromptAsset]:
    """获取 Prompt 资产。"""
    return db.query(ManagedAgentPromptAsset).filter(
        ManagedAgentPromptAsset.managed_agent_id == managed_agent_id
    ).first()


def update_prompt_asset(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentPromptAsset:
    """更新 Prompt 资产。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    prompt_asset = _ensure_prompt_asset(db, agent)
    normalized = _normalize_prompt_asset_kwargs(kwargs)

    changed = False
    for key, value in normalized.items():
        if value is not None and hasattr(prompt_asset, key) and getattr(prompt_asset, key) != value:
            setattr(prompt_asset, key, value)
            changed = True

    if changed:
        prompt_asset.authority_source = "database"
        prompt_asset.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(prompt_asset)
    return prompt_asset


def reset_prompt_from_template(db: Session, managed_agent_id: str) -> ManagedAgentPromptAsset:
    """从角色模板重新初始化 Prompt 资产。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    prompt_asset = _ensure_prompt_asset(db, agent)

    template_dir = os.path.join(os.getcwd(), "prompts", "templates")
    role = agent.role
    candidate_files = [
        os.path.join(template_dir, f"{role}.md"),
        os.path.join(template_dir, f"task-{role}.md"),
    ]
    template_file = next((path for path in candidate_files if os.path.exists(path)), None)

    if not template_file:
        raise ValueError(f"角色模板不存在: {role}")

    with open(template_file, "r", encoding="utf-8") as f:
        prompt_asset.system_prompt_content = f.read()

    prompt_asset.template_role = role
    prompt_asset.host_render_strategy = _default_render_strategy(agent.host_platform, agent.deployment_mode)
    prompt_asset.authority_source = "database"
    prompt_asset.updated_at = datetime.now()
    _bump_config_version(db, agent)

    db.commit()
    db.refresh(prompt_asset)
    return prompt_asset


def render_prompt_preview(db: Session, managed_agent_id: str) -> Dict[str, object]:
    """按宿主平台渲染 Prompt 预览。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    prompt_asset = _ensure_prompt_asset(db, agent)

    if agent.host_platform == "openclaw":
        artifacts = [
            {"name": "AGENTS.md", "content": prompt_asset.system_prompt_content or ""},
            {"name": "SOUL.md", "content": prompt_asset.persona_prompt_content or ""},
            {"name": "IDENTITY.md", "content": prompt_asset.identity_content or ""},
        ]
    else:
        artifacts = [
            {"name": "system_prompt.txt", "content": prompt_asset.system_prompt_content or ""},
            {"name": "persona_prompt.txt", "content": prompt_asset.persona_prompt_content or ""},
            {"name": "identity.txt", "content": prompt_asset.identity_content or ""},
        ]

    return {
        "host_platform": agent.host_platform,
        "host_render_strategy": prompt_asset.host_render_strategy,
        "artifacts": artifacts,
    }


def list_schedules(db: Session, managed_agent_id: str) -> List[ManagedAgentSchedule]:
    """获取 Agent 的所有定时任务。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return db.query(ManagedAgentSchedule).filter(
        ManagedAgentSchedule.managed_agent_id == managed_agent_id
    ).all()


def get_schedule_or_404(db: Session, schedule_id: str) -> ManagedAgentSchedule:
    """获取定时任务，不存在则抛异常。"""
    schedule = db.query(ManagedAgentSchedule).filter(
        ManagedAgentSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise ValueError(f"定时任务不存在: {schedule_id}")
    return schedule


def create_schedule(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentSchedule:
    """创建定时任务。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    normalized = _normalize_schedule_kwargs(kwargs)

    schedule = ManagedAgentSchedule(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        **normalized,
    )
    db.add(schedule)
    _bump_config_version(db, agent)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule(db: Session, schedule_id: str, **kwargs) -> ManagedAgentSchedule:
    """更新定时任务。"""
    schedule = get_schedule_or_404(db, schedule_id)
    agent = get_managed_agent_or_404(db, schedule.managed_agent_id)
    normalized = _normalize_schedule_kwargs(kwargs, schedule.execution_options_json)

    changed = False
    for key, value in normalized.items():
        if value is not None and hasattr(schedule, key) and getattr(schedule, key) != value:
            setattr(schedule, key, value)
            changed = True

    if changed:
        schedule.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule_id: str) -> None:
    """删除定时任务。"""
    schedule = get_schedule_or_404(db, schedule_id)
    agent = get_managed_agent_or_404(db, schedule.managed_agent_id)
    db.delete(schedule)
    _bump_config_version(db, agent)
    db.commit()


def list_comm_bindings(db: Session, managed_agent_id: str) -> List[ManagedAgentCommBinding]:
    """获取通讯平台账号绑定。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return db.query(ManagedAgentCommBinding).filter(
        ManagedAgentCommBinding.managed_agent_id == managed_agent_id
    ).all()


def get_comm_binding_or_404(db: Session, binding_id: str) -> ManagedAgentCommBinding:
    """获取通讯平台账号绑定，不存在则抛异常。"""
    binding = db.query(ManagedAgentCommBinding).filter(
        ManagedAgentCommBinding.id == binding_id
    ).first()
    if not binding:
        raise ValueError(f"通讯平台账号绑定不存在: {binding_id}")
    return binding


def create_comm_binding(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentCommBinding:
    """创建通讯平台账号绑定。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    normalized = _normalize_comm_binding_kwargs(kwargs)

    if not normalized.get("provider") or not normalized.get("binding_key"):
        raise ValueError("provider 和 binding_key 不能为空")

    binding = ManagedAgentCommBinding(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        **normalized,
    )
    db.add(binding)
    _bump_config_version(db, agent)
    db.commit()
    db.refresh(binding)
    return binding


def update_comm_binding(db: Session, binding_id: str, **kwargs) -> ManagedAgentCommBinding:
    """更新通讯平台账号绑定。"""
    binding = get_comm_binding_or_404(db, binding_id)
    agent = get_managed_agent_or_404(db, binding.managed_agent_id)
    normalized = _normalize_comm_binding_kwargs(kwargs)

    changed = False
    for key, value in normalized.items():
        if value is not None and hasattr(binding, key) and getattr(binding, key) != value:
            setattr(binding, key, value)
            changed = True

    if changed:
        binding.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(binding)
    return binding


def delete_comm_binding(db: Session, binding_id: str) -> None:
    """删除通讯平台账号绑定。"""
    binding = get_comm_binding_or_404(db, binding_id)
    agent = get_managed_agent_or_404(db, binding.managed_agent_id)
    db.delete(binding)
    _bump_config_version(db, agent)
    db.commit()


def list_notification_channels(db: Session, managed_agent_id: str) -> List[ManagedAgentNotificationChannel]:
    """获取通知渠道。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return db.query(ManagedAgentNotificationChannel).filter(
        ManagedAgentNotificationChannel.managed_agent_id == managed_agent_id
    ).all()


def get_notification_channel_or_404(db: Session, channel_id: str) -> ManagedAgentNotificationChannel:
    """获取通知渠道，不存在则抛异常。"""
    channel = db.query(ManagedAgentNotificationChannel).filter(
        ManagedAgentNotificationChannel.id == channel_id
    ).first()
    if not channel:
        raise ValueError(f"通知渠道不存在: {channel_id}")
    return channel


def create_notification_channel(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentNotificationChannel:
    """创建通知渠道。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    channel = ManagedAgentNotificationChannel(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        **kwargs,
    )
    db.add(channel)
    _bump_config_version(db, agent)
    db.commit()
    db.refresh(channel)
    return channel


def update_notification_channel(db: Session, channel_id: str, **kwargs) -> ManagedAgentNotificationChannel:
    """更新通知渠道。"""
    channel = get_notification_channel_or_404(db, channel_id)
    agent = get_managed_agent_or_404(db, channel.managed_agent_id)
    changed = False
    for key, value in kwargs.items():
        if value is not None and hasattr(channel, key) and getattr(channel, key) != value:
            setattr(channel, key, value)
            changed = True

    if changed:
        channel.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(channel)
    return channel


def delete_notification_channel(db: Session, channel_id: str) -> None:
    """删除通知渠道。"""
    channel = get_notification_channel_or_404(db, channel_id)
    agent = get_managed_agent_or_404(db, channel.managed_agent_id)
    db.delete(channel)
    _bump_config_version(db, agent)
    db.commit()


def auto_backfill_from_runtime(db: Session) -> None:
    """
    把已有的运行态 agent 回填到 managed_agent。
    幂等：通过 runtime_agent_id 去重，多次执行不报错。
    """
    agents = db.query(Agent).all()
    success, skipped, failed = 0, 0, 0

    for runtime_agent in agents:
        try:
            existing = db.query(ManagedAgent).filter(
                ManagedAgent.runtime_agent_id == runtime_agent.id
            ).first()
            if existing:
                skipped += 1
                continue

            slug = _generate_slug(runtime_agent.name)
            base_slug = slug
            counter = 1
            while db.query(ManagedAgent).filter(ManagedAgent.slug == slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            managed = ManagedAgent(
                id=str(uuid.uuid4()),
                name=runtime_agent.name,
                slug=slug,
                role=runtime_agent.role,
                description=runtime_agent.description or "",
                host_platform="openclaw",
                deployment_mode="bind_existing_agent",
                host_access_mode="local",
                status="deployed",
                runtime_agent_id=runtime_agent.id,
                config_version=1,
                deployed_config_version=1,
            )
            db.add(managed)
            db.flush()

            db.add(ManagedAgentHostConfig(
                id=str(uuid.uuid4()),
                managed_agent_id=managed.id,
                host_platform=managed.host_platform,
            ))
            db.add(ManagedAgentPromptAsset(
                id=str(uuid.uuid4()),
                managed_agent_id=managed.id,
                template_role=managed.role,
                host_render_strategy=_default_render_strategy(managed.host_platform, managed.deployment_mode),
                authority_source="database",
            ))

            db.commit()
            success += 1
        except Exception as exc:
            db.rollback()
            failed += 1
            print(f"[ManagedAgent] 回填失败 (跳过): agent={runtime_agent.name}, error={exc}")

    if success or failed:
        print(f"[ManagedAgent] 回填完成: 成功={success}, 跳过={skipped}, 失败={failed}")


def serialize_host_config(host_config: ManagedAgentHostConfig) -> Dict[str, object]:
    """把宿主配置模型转成 API 响应 dict。"""
    return {
        "id": host_config.id,
        "managed_agent_id": host_config.managed_agent_id,
        "host_platform": host_config.host_platform,
        "host_agent_identifier": host_config.host_agent_identifier,
        "workdir_path": host_config.workdir_path,
        "default_model": host_config.default_model,
        "host_config_payload_masked": _mask(host_config.host_config_payload_encrypted),
        "host_metadata_json": host_config.host_metadata_json,
        "created_at": host_config.created_at,
        "updated_at": host_config.updated_at,
    }


def serialize_comm_binding(binding: ManagedAgentCommBinding) -> Dict[str, object]:
    """把通讯平台账号绑定模型转成 API 响应 dict。"""
    return {
        "id": binding.id,
        "managed_agent_id": binding.managed_agent_id,
        "provider": binding.provider,
        "binding_key": binding.binding_key,
        "display_name": binding.display_name,
        "enabled": binding.enabled,
        "routing_policy_json": binding.routing_policy_json,
        "metadata_json": binding.metadata_json,
        "config_payload_masked": _mask(binding.config_payload_encrypted),
        "created_at": binding.created_at,
        "updated_at": binding.updated_at,
    }
