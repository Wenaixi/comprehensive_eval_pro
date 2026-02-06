import os
import tempfile
import unittest

from comprehensive_eval_pro.utils.image_convert import cleanup_temp_file, ensure_jpg


class TestImageConvert(unittest.TestCase):
    def test_ensure_jpg_passthrough_for_jpg(self):
        with tempfile.TemporaryDirectory() as tmp:
            jpg_path = os.path.join(tmp, "a.jpg")
            with open(jpg_path, "wb") as f:
                f.write(b"\xff\xd8\xff\xd9")
            out, cleanup = ensure_jpg(jpg_path)
            self.assertEqual(out, jpg_path)
            self.assertFalse(cleanup)

    @unittest.skipUnless(__import__("importlib").util.find_spec("PIL") is not None, "Pillow not installed")
    def test_ensure_jpg_converts_png(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            png_path = os.path.join(tmp, "a.png")
            Image.new("RGB", (10, 10), (10, 20, 30)).save(png_path, format="PNG")

            out, cleanup = ensure_jpg(png_path)
            self.assertNotEqual(out, png_path)
            self.assertTrue(cleanup)
            self.assertTrue(os.path.exists(out))
            with open(out, "rb") as f:
                header = f.read(2)
            self.assertEqual(header, b"\xff\xd8")
            cleanup_temp_file(out, cleanup)
            self.assertFalse(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()

