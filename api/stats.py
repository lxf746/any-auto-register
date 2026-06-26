"""Registration success rate dashboard API."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from sqlmodel import Session, select, func, text

from core.datetime_utils import _utcnow
from core.db import TaskLog, ProxyModel, AccountModel, AccountOverviewModel, engine

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def stats_overview():
    """Global overview: total registrations, success rate, account status distribution."""
    with Session(engine) as session:
        total = int(session.exec(
            select(func.count()).select_from(TaskLog)
        ).one() or 0)
        success = int(session.exec(
            select(func.count()).select_from(TaskLog)
            .where(TaskLog.status == "success")
        ).one() or 0)
        failed = total - success

        # Account status distribution
        statuses = session.exec(
            select(
                AccountOverviewModel.lifecycle_status,
                func.count(),
            ).group_by(AccountOverviewModel.lifecycle_status)
        ).all()
        account_distribution = {row[0]: row[1] for row in statuses}

        # Total accounts
        total_accounts = int(session.exec(
            select(func.count()).select_from(AccountModel)
        ).one() or 0)

    return {
        "total_registrations": total,
        "success": success,
        "failed": failed,
        "success_rate": round(success / total * 100, 1) if total else 0,
        "total_accounts": total_accounts,
        "account_distribution": account_distribution,
    }


@router.get("/by-platform")
def stats_by_platform():
    """Statistics by platform: success rate."""
    with Session(engine) as session:
        rows = session.exec(
            select(
                TaskLog.platform,
                TaskLog.status,
                func.count(),
            ).group_by(TaskLog.platform, TaskLog.status)
        ).all()

    platforms: dict[str, dict] = {}
    for platform, status, count in rows:
        if platform not in platforms:
            platforms[platform] = {"platform": platform, "success": 0, "failed": 0, "total": 0}
        if status == "success":
            platforms[platform]["success"] += count
        else:
            platforms[platform]["failed"] += count
        platforms[platform]["total"] += count

    for p in platforms.values():
        p["success_rate"] = round(p["success"] / p["total"] * 100, 1) if p["total"] else 0

    return sorted(platforms.values(), key=lambda x: x["total"], reverse=True)


@router.get("/by-day")
def stats_by_day(days: int = 30, platform: str = ""):
    """Daily registration trends."""
    cutoff = _utcnow() - timedelta(days=days)
    with Session(engine) as session:
        q = select(TaskLog).where(TaskLog.created_at >= cutoff)
        if platform:
            q = q.where(TaskLog.platform == platform)
        logs = session.exec(q.order_by(TaskLog.created_at)).all()

    daily: dict[str, dict] = {}
    for log in logs:
        day = log.created_at.strftime("%Y-%m-%d") if log.created_at else "unknown"
        if day not in daily:
            daily[day] = {"date": day, "success": 0, "failed": 0, "total": 0}
        if log.status == "success":
            daily[day]["success"] += 1
        else:
            daily[day]["failed"] += 1
        daily[day]["total"] += 1

    for d in daily.values():
        d["success_rate"] = round(d["success"] / d["total"] * 100, 1) if d["total"] else 0

    return sorted(daily.values(), key=lambda x: x["date"])


@router.get("/by-proxy")
def stats_by_proxy():
    """Proxy success rate ranking."""
    with Session(engine) as session:
        proxies = session.exec(
            select(ProxyModel).order_by(ProxyModel.success_count.desc())
        ).all()

    return [
        {
            "id": p.id,
            "url": p.url,
            "region": p.region,
            "success": p.success_count,
            "fail": p.fail_count,
            "total": p.success_count + p.fail_count,
            "success_rate": round(
                p.success_count / (p.success_count + p.fail_count) * 100, 1
            ) if (p.success_count + p.fail_count) else 0,
            "is_active": p.is_active,
        }
        for p in proxies
    ]


@router.get("/errors")
def stats_errors(days: int = 7, platform: str = "", limit: int = 20):
    """Recent failure error aggregation (grouped by error message)."""
    cutoff = _utcnow() - timedelta(days=days)
    with Session(engine) as session:
        q = (
            select(TaskLog.error, func.count().label("count"))
            .where(TaskLog.status == "failed")
            .where(TaskLog.created_at >= cutoff)
            .where(TaskLog.error != "")
        )
        if platform:
            q = q.where(TaskLog.platform == platform)
        q = q.group_by(TaskLog.error).order_by(func.count().desc()).limit(limit)
        rows = session.exec(q).all()

    return [{"error": row[0], "count": row[1]} for row in rows]
