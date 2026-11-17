def parse_user(row):
    return {
        "user_id": int(row["id"]),
        "email": row["email"].lower(),
        "active": bool(row.get("active", True)),
    }
