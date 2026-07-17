import unittest.mock as mock
from app.services.email_service import send_magic_link

def test_send_magic_link():
    with mock.patch("resend.Emails.send") as mock_send:
        send_magic_link("test@example.com", "http://magic.link/123")
        mock_send.assert_called_once()
        args = mock_send.call_args[0][0]
        assert args["to"] == "test@example.com"
        assert "http://magic.link/123" in args["html"]
