"""Research reports API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from hivemind.db.models import ResearchReportRow
from hivemind.db.session import get_db

router = APIRouter(prefix="/research", tags=["research"])


class ResearchReport(BaseModel):
    id: str
    researcher: str
    report_type: str
    title: str
    summary: str | None
    findings: dict | None
    recommendations: list | dict | None
    data_context: dict | None
    created_at: str


@router.get("/reports", response_model=list[ResearchReport])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    researcher: str | None = None,
    report_type: str | None = None,
    limit: int = 20,
):
    """List research reports with optional filters."""
    query = select(ResearchReportRow).order_by(desc(ResearchReportRow.created_at)).limit(limit)
    if researcher:
        query = query.where(ResearchReportRow.researcher == researcher)
    if report_type:
        query = query.where(ResearchReportRow.report_type == report_type)
    result = await db.execute(query)
    reports = result.scalars().all()
    return [
        ResearchReport(
            id=str(r.id),
            researcher=r.researcher,
            report_type=r.report_type,
            title=r.title,
            summary=r.summary,
            findings=r.findings,
            recommendations=r.recommendations,
            data_context=r.data_context,
            created_at=r.created_at.isoformat(),
        )
        for r in reports
    ]


@router.get("/reports/{report_id}", response_model=ResearchReport)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single research report by ID."""
    from uuid import UUID
    result = await db.execute(
        select(ResearchReportRow).where(ResearchReportRow.id == UUID(report_id))
    )
    r = result.scalar_one_or_none()
    if r is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return ResearchReport(
        id=str(r.id),
        researcher=r.researcher,
        report_type=r.report_type,
        title=r.title,
        summary=r.summary,
        findings=r.findings,
        recommendations=r.recommendations,
        data_context=r.data_context,
        created_at=r.created_at.isoformat(),
    )


@router.get("/latest")
async def latest_reports(
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent report of each type."""
    from sqlalchemy import func

    # Get distinct report types
    types_result = await db.execute(
        select(ResearchReportRow.report_type).distinct()
    )
    report_types = [r[0] for r in types_result.all()]

    latest = []
    for rt in report_types:
        result = await db.execute(
            select(ResearchReportRow)
            .where(ResearchReportRow.report_type == rt)
            .order_by(desc(ResearchReportRow.created_at))
            .limit(1)
        )
        r = result.scalar_one_or_none()
        if r:
            latest.append(ResearchReport(
                id=str(r.id),
                researcher=r.researcher,
                report_type=r.report_type,
                title=r.title,
                summary=r.summary,
                findings=r.findings,
                recommendations=r.recommendations,
                data_context=r.data_context,
                created_at=r.created_at.isoformat(),
            ))
    return latest
