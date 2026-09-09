from app.models.schemas import PageAnalysis, DocumentGroup


def group_pages(pages: list[PageAnalysis]) -> list[DocumentGroup]:
    """Group consecutive pages of the same type. FORM_8014 chains keep first/last page."""
    if not pages:
        return []
    groups: list[DocumentGroup] = []
    current = [pages[0]]
    for page in pages[1:]:
        prev = current[-1]
        same_type = page.classification == prev.classification
        # Allow UNKNOWN to attach to ongoing FORM_ groups (continuation pages)
        merge_unknown = (
            page.classification == "UNKNOWN"
            and prev.classification.startswith("FORM_")
        )
        if same_type or merge_unknown:
            current.append(page)
        else:
            groups.append(_make_group(len(groups) + 1, current))
            current = [page]
    groups.append(_make_group(len(groups) + 1, current))
    return groups


def _make_group(n: int, pages: list[PageAnalysis]) -> DocumentGroup:
    primary = pages[0].classification
    page_nums = [p.page for p in pages]
    return DocumentGroup(
        group_id=f"G{n:03d}",
        type=primary,
        pages=page_nums,
        first_page=min(page_nums),
        last_page=max(page_nums),
        confidence=round(sum(p.confidence for p in pages) / len(pages), 3),
        continuation=len(pages) > 1,
    )
