def mask_nric(nric: str) -> str:
    """Mask NRIC for display/export.

    Rules:
    - Keep raw NRIC stored internally (caller should not persist masked value).
    - When displaying, mask the first 5 characters with '*'.
    - Handle empty/None safely.
    - If NRIC shorter than 5 chars, mask all but last max(0, len-5) -> effectively mask everything.

    Example:
    S1234567A -> *****567A
    """
    if not nric:
        return ""

    s = str(nric)
    if len(s) <= 5:
        return "*" * len(s)

    return "*" * 5 + s[5:]
