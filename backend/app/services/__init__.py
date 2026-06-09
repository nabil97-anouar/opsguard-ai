"""Service package exports."""

def seed_demo_data(*, reset: bool = False):
    from app.services.demo_seed import seed_demo_data as _seed_demo_data

    return _seed_demo_data(reset=reset)


__all__ = ["seed_demo_data"]
