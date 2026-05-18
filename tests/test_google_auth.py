import unittest
from unittest.mock import mock_open, patch

from backend.services import google_auth


class FakeCredentials:
    valid = True
    expired = False
    refresh_token = None

    def to_json(self):
        return '{"token": "demo"}'


class FakeFlow:
    def run_local_server(self, port=0):
        return FakeCredentials()


class GoogleAuthTest(unittest.TestCase):
    def test_authenticate_google_runs_browser_flow_when_no_token_exists(self):
        with patch.object(google_auth.os.path, "exists", return_value=False), patch.object(
            google_auth.google_auth_oauthlib.flow.InstalledAppFlow,
            "from_client_secrets_file",
            return_value=FakeFlow(),
        ) as flow_factory, patch("builtins.open", mock_open()) as opened:
            creds = google_auth.authenticate_google()

        self.assertTrue(creds.valid)
        flow_factory.assert_called_once_with(google_auth.CLIENT_SECRETS_FILE, google_auth.SCOPES)
        opened.assert_called_once_with("token.json", "w")
        opened().write.assert_called_once_with('{"token": "demo"}')

    def test_initialize_youtube_api_builds_client_with_credentials(self):
        credentials = FakeCredentials()
        youtube = object()
        with patch.object(google_auth, "authenticate_google", return_value=credentials), patch.object(
            google_auth.googleapiclient.discovery,
            "build",
            return_value=youtube,
        ) as build:
            result = google_auth.initialize_youtube_api()

        self.assertIs(result, youtube)
        build.assert_called_once_with("youtube", "v3", credentials=credentials)


if __name__ == "__main__":
    unittest.main()
