"""CLI入口。"""
from __future__ import annotations
import argparse
from pathlib import Path

from lumos.dotenv import find_and_load


def main() -> int:
    # 在解析参数前自动加载 .env 到 os.environ。
    # 这样 ``config.yaml`` 里的 ``${VAR}`` 替换就能从 .env 拿到值。
    # 已存在的环境变量不会被覆盖；CLI 用户显式 export 总是优先。
    find_and_load(Path.cwd(), override=False)

    p = argparse.ArgumentParser(prog="lumos")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="Run Lumos server")
    s.add_argument("--config", "-c", default="./config.yaml")

    a = sub.add_parser("admin", help="Admin commands")
    a_sub = a.add_subparsers(dest="admin_cmd", required=True)
    a_create = a_sub.add_parser("create", help="Create admin user")
    a_create.add_argument("--email", required=True)
    a_create.add_argument("--password", required=True)
    a_create.add_argument("--config", "-c", default="./config.yaml")

    args = p.parse_args()
    if args.cmd == "serve":
        from lumos.server import run
        run(args.config)
        return 0
    if args.cmd == "admin" and args.admin_cmd == "create":
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from lumos.config import load_config, set_config
        from lumos.persistence.db import get_engine, init_db
        from lumos.persistence.repositories.users import UserRepository
        from lumos.api.auth_utils import hash_password
        import asyncio

        async def _create():
            cfg = load_config(args.config)
            set_config(cfg)
            eng = get_engine(cfg.db.url)
            await init_db(eng)
            factory = async_sessionmaker(eng, expire_on_commit=False)
            async with factory() as db:
                repo = UserRepository(db)
                if await repo.get_by_email(args.email):
                    print(f"User {args.email} already exists")
                    return
                await repo.create(
                    email=args.email,
                    password_hash=hash_password(args.password, rounds=cfg.auth.bcrypt_rounds),
                )
                print(f"Created admin: {args.email}")
            await eng.dispose()
        asyncio.run(_create())
        return 0
    p.print_help()
    return 1