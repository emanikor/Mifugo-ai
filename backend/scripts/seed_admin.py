"""
One-time seed script to create initial accounts. There's no self-service
signup in this app on purpose — new agents/officials should be added
deliberately by an admin, since accounts here map to accountable individuals
entering real market data.

Run once, after the containers are up:
    docker compose exec backend python -m scripts.seed_admin
"""
from getpass import getpass

from app.database import SessionLocal
from app.models import Agent
from app.security import hash_password


def main():
    db = SessionLocal()
    try:
        username = input("Username: ").strip()
        full_name = input("Full name: ").strip()
        role = input("Role [agent/official/admin] (default: admin): ").strip() or "admin"
        password = getpass("Password: ")

        if db.query(Agent).filter(Agent.username == username).first():
            print(f"User '{username}' already exists.")
            return

        agent = Agent(
            username=username,
            full_name=full_name,
            role=role,
            password_hash=hash_password(password),
        )
        db.add(agent)
        db.commit()
        print(f"Created {role} account '{username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
