"""
managed_agent 核心 CRUD 与回填逻辑。
"""

import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.managed_agent import (
    ManagedAgent,
    ManagedAgentCommBinding,
    ManagedAgentHostConfig,
    ManagedAgentPromptAsset,
    ManagedAgentSchedule,
)

from .shared import _bump_config_version, _default_render_strategy, _generate_slug


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

    db.add(
        ManagedAgentHostConfig(
            id=str(uuid.uuid4()),
            managed_agent_id=agent.id,
            host_platform=host_platform,
            host_agent_identifier=host_agent_identifier,
            workdir_path=workdir_path,
        )
    )
    db.add(
        ManagedAgentPromptAsset(
            id=str(uuid.uuid4()),
            managed_agent_id=agent.id,
            template_role=role,
            host_render_strategy=_default_render_strategy(host_platform, deployment_mode),
            authority_source="database",
        )
    )

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

    db.delete(agent)
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

            db.add(
                ManagedAgentHostConfig(
                    id=str(uuid.uuid4()),
                    managed_agent_id=managed.id,
                    host_platform=managed.host_platform,
                )
            )
            db.add(
                ManagedAgentPromptAsset(
                    id=str(uuid.uuid4()),
                    managed_agent_id=managed.id,
                    template_role=managed.role,
                    host_render_strategy=_default_render_strategy(
                        managed.host_platform, managed.deployment_mode
                    ),
                    authority_source="database",
                )
            )

            db.commit()
            success += 1
        except Exception as exc:
            db.rollback()
            failed += 1
            print(f"[ManagedAgent] 回填失败 (跳过): agent={runtime_agent.name}, error={exc}")

    if success or failed:
        print(f"[ManagedAgent] 回填完成: 成功={success}, 跳过={skipped}, 失败={failed}")
