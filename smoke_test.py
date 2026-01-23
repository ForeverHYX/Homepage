from app.main import app


def main() -> None:
    assert app.title == "Foreverhyx Homepage"
    print("smoke test ok")


if __name__ == "__main__":
    main()
