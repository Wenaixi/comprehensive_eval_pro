from __future__ import annotations


def compute_base_entries(
    *,
    tasks: list[dict],
    selection: str,
    indices: list[int],
    looks_like_class_meeting,
    is_y_special_task,
    is_labor_task=None,
):
    selection = (selection or "").lower()
    base_entries: list[tuple[int, dict]] = []

    if selection == "y":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if is_y_special_task(t)]
    elif selection == "jx":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if "军训" in (t.get("name", "") or "")]
    elif selection == "gq":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if "国旗下讲话" in (t.get("name", "") or "")]
    elif selection == "ld":
        # 逻辑统一：优先使用专业的 is_labor_task 逻辑
        if is_labor_task:
            base_entries = [(idx, t) for idx, t in enumerate(tasks) if is_labor_task(t.get("name", ""), t.get("dimensionName", ""))]
        else:
            # 垫底逻辑
            base_entries = [(idx, t) for idx, t in enumerate(tasks) if "劳动" in (t.get("name", "") or "") and not looks_like_class_meeting(t)]
    elif selection == "bh":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if looks_like_class_meeting(t)]
    elif selection == "indices":
        for idx in indices:
            if 0 <= idx < len(tasks):
                base_entries.append((idx, tasks[idx]))

    return base_entries


def compute_target_entries(
    *,
    base_entries: list[tuple[int, dict]],
    scope: str,
    get_task_status,
    is_pending_status,
):
    scope = (scope or "pending").lower()
    if scope not in {"pending", "done", "all"}:
        scope = "pending"

    target_entries: list[tuple[int, dict]] = []
    done_count = 0
    pending_count = 0

    for idx, t in base_entries:
        pending = is_pending_status(get_task_status(t))
        if pending:
            pending_count += 1
        else:
            done_count += 1
        if scope == "pending" and pending:
            target_entries.append((idx, t))
        elif scope == "done" and (not pending):
            target_entries.append((idx, t))
        elif scope == "all":
            target_entries.append((idx, t))

    return target_entries, pending_count, done_count


def get_or_init_gen_counts(preset: dict) -> dict:
    gen_counts = preset.get("gen_counts")
    if not isinstance(gen_counts, dict):
        gen_counts = {}
        preset["gen_counts"] = gen_counts
    return gen_counts


def should_use_cache_for_task(*, preset: dict, task_name: str, diversity_every: int, should_use_cache) -> bool:
    gen_counts = get_or_init_gen_counts(preset)
    current_count = int(gen_counts.get(task_name, 0) or 0)
    return should_use_cache(current_count, diversity_every)


def mark_task_generated(*, preset: dict, task_name: str):
    gen_counts = get_or_init_gen_counts(preset)
    gen_counts[task_name] = int(gen_counts.get(task_name, 0) or 0) + 1

