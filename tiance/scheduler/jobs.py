from collections.abc import Callable


def register_jobs(app) -> None:
    scheduler = app.state.scheduler
    admin_service = app.state.admin_service

    job_functions: dict[str, Callable[[], int]] = {
        "fetch_announcements": app.state.announcement_service.fetch_all_watchlist,
        "fetch_rank_list": lambda: 0,
        "fetch_money_flow": lambda: 0,
    }
    admin_service.job_functions.update(job_functions)

    scheduler.add_job(
        lambda: admin_service.run_task("fetch_announcements", job_functions["fetch_announcements"]),
        trigger="cron",
        minute=5,
        id="fetch_announcements",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: admin_service.run_task("fetch_rank_list", job_functions["fetch_rank_list"]),
        trigger="cron",
        day_of_week="mon-fri",
        hour=16,
        minute=30,
        id="fetch_rank_list",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: admin_service.run_task("fetch_money_flow", job_functions["fetch_money_flow"]),
        trigger="cron",
        day_of_week="mon-fri",
        hour=16,
        minute=30,
        id="fetch_money_flow",
        replace_existing=True,
    )
