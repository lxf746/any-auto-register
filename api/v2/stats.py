"""v2 Stats endpoints — registration statistics dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import case
from sqlmodel import Session, func, select

from core.db import (
    AccountModel,
    AccountOverviewModel,
    ProxyModel,
    TaskLog,
    engine,
)
from api.v2.response import ApiResponse

router = APIRouter(prefix="/stats", tags=["stats"])


# ---------------------------------------------------------------------------
# GET /overview
# ---------------------------------------------------------------------------


@router.get("/overview")
def stats_overview():
    """Global overview: total registrations, success rate, account distribution."""
    with Session(engine) as session:
        total = int(
            session.exec(select(func.count()).select_from(TaskLog)).one() or 0
        )
        success = int(
            session.exec(
                select(func.count())
                .select_from(TaskLog)
                .where(TaskLog.status == "success")
            ).one()
            or 0
        )
        failed = total - success

        statuses = session.exec(
            select(
                AccountOverviewModel.lifecycle_status,
                func.count(),
            ).group_by(AccountOverviewModel.lifecycle_status)
        ).all()
        account_distribution = {row[0]: row[1] for row in statuses}

        total_accounts = int(
            session.exec(select(func.count()).select_from(AccountModel)).one() or 0
        )

    return ApiResponse(
        ok=True,
        data={
            "total_registrations": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "total_accounts": total_accounts,
            "account_distribution": account_distribution,
        },
    )


# ---------------------------------------------------------------------------
# GET /by-platform
# ---------------------------------------------------------------------------


@router.get("/by-platform")
def stats_by_platform():
    """Per-platform registration breakdown with success rates."""
    with Session(engine) as session:
        rows = session.exec(
            select(
                TaskLog.platform,
                func.count(),
                func.sum(case((TaskLog.status == "success", 1), else_=0)),
            ).group_by(TaskLog.platform)
        ).all()

    result = []
    for platform, total, success in rows:
        total = int(total or 0)
        success = int(success or 0)
        result.append(
            {
                "platform": platform,
                "total": total,
                "success": success,
                "failed": total - success,
                "success_rate": round(success / total * 100, 1) if total else 0,
            }
        )

    return ApiResponse(ok=True, data=result)


# ---------------------------------------------------------------------------
# GET /by-day
# ---------------------------------------------------------------------------


@router.get("/by-day")
def stats_by_day(
    days: int = Query(default=30, ge=1, le=365),
    platform: str = Query(default=""),
):
    """Daily registration timeline for the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with Session(engine) as session:
        stmt = (
            select(
                func.date(TaskLog.created_at).label("day"),
                TaskLog.platform,
                func.count(),
                func.sum(case((TaskLog.status == "success", 1), else_=0)),
            )
            .where(TaskLog.created_at >= cutoff)
            .group_by(func.date(TaskLog.created_at), TaskLog.platform)
        )

        if platform:
            stmt = stmt.where(TaskLog.platform == platform)

        rows = session.exec(stmt).all()

    # Aggregate by day (sum across platforms if no filter)
    by_day: dict[str, dict] = {}
    for day, _plat, total, success in rows:
        day_str = str(day)
        if day_str not in by_day:
            by_day[day_str] = {"date": day_str, "total": 0, "success": 0, "failed": 0}
        by_day[day_str]["total"] += int(total or 0)
        by_day[day_str]["success"] += int(success or 0)
        by_day[day_str]["failed"] += int(total or 0) - int(success or 0)

    result = sorted(by_day.values(), key=lambda x: x["date"])
    return ApiResponse(ok=True, data=result)


# ---------------------------------------------------------------------------
# GET /by-proxy
# ---------------------------------------------------------------------------


@router.get("/by-proxy")
def stats_by_proxy():
    """Per-proxy performance metrics."""
    with Session(engine) as session:
        proxies = session.exec(
            select(ProxyModel).where(ProxyModel.is_active == True)  # noqa: E712
        ).all()

    result = []
    for p in proxies:
        total = p.success_count + p.fail_count
        result.append(
            {
                "url": p.url,
                "region": p.region,
                "total": total,
                "success": p.success_count,
                "failed": p.fail_count,
                "success_rate": round(p.success_count / total * 100, 1) if total else 0,
            }
        )

    return ApiResponse(ok=True, data=result)


# ---------------------------------------------------------------------------
# GET /errors
# ---------------------------------------------------------------------------


@router.get("/errors")
def stats_errors(
    days: int = Query(default=30, ge=1, le=365),
    platform: str = Query(default=""),
):
    """Error distribution by platform and message."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with Session(engine) as session:
        stmt = (
            select(
                TaskLog.platform,
                TaskLog.error,
                func.count(),
            )
            .where(TaskLog.status == "failed")
            .where(TaskLog.created_at >= cutoff)
            .where(TaskLog.error != "")
            .group_by(TaskLog.platform, TaskLog.error)
        )

        if platform:
            stmt = stmt.where(TaskLog.platform == platform)

        rows = session.exec(stmt).all()

    result = [
        {"platform": plat, "error": err, "count": int(cnt)}
        for plat, err, cnt in rows
    ]

    return ApiResponse(ok=True, data=result)
