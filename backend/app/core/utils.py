from typing import Optional

from fastapi import HTTPException, status


def get_pagination(limit: Optional[int], offset: Optional[int]) -> tuple[int, int]:
    limit = limit or 100
    offset = offset or 0
    if limit <= 0 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le paramètre limit doit être compris entre 1 et 1000",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le paramètre offset doit être positif ou nul",
        )
    return limit, offset


def paginated_response(items, total: int, limit: int, offset: int) -> dict:
    return {
        "items": items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        },
    }
