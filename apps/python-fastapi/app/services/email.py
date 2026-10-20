import logging

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    # TODO: wire up the transactional email provider; log for now so QA can follow the flow.
    logger.info("Sending email to=%s subject=%s body=%s", to, subject, body)
