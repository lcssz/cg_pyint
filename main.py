from core import Core


def main() -> None:
    cc_core = Core(800, 600)
    try:
        cc_core.run()
    finally:
        cc_core.deinit()


if __name__ == "__main__":
    main()
