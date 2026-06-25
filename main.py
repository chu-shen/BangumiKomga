from tools.log import init_logger
from services.service_runner import run_service


def main():
    init_logger()
    run_service()


if __name__ == "__main__":
    main()
