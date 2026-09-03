from app.models.schemas import PageAnalysis, DocumentGroup

def group_pages(pages: list[PageAnalysis]) -> list[DocumentGroup]:
    if not pages:
        return []
    groups: list[DocumentGroup] = []
    current = [pages[0]]
    for page in pages[1:]:
        prev = current[-1]
        same_type = page.classification == prev.classification
        merge_unknown = page.classification == 'UNKNOWN' and prev.classification.startswith('FORM_')
        if same_type or merge_unknown:
            current.append(page)
        else:
            groups.append(_make_group(len(groups)+1, current))
            current = [page]
    groups.append(_make_group(len(groups)+1, current))
    return groups

def _make_group(n: int, pages: list[PageAnalysis]) -> DocumentGroup:
    primary = pages[0].classification
    return DocumentGroup(group_id=f'G{n:03d}', type=primary, pages=[p.page for p in pages], confidence=round(sum(p.confidence for p in pages)/len(pages), 3), continuation=len(pages)>1)
