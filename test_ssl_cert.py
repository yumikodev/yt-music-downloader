import os
import unittest

import main


class TestSSLCertConfig(unittest.TestCase):
    def test_configure_ssl_env_sets_valid_cert_path(self):
        cert_path = main.configure_ssl_env()
        self.assertTrue(cert_path)
        self.assertTrue(os.path.exists(cert_path))


if __name__ == "__main__":
    unittest.main()
