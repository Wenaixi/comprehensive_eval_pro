import argparse
import os
from .policy import config
from comprehensive_eval_pro.services.captcha_ocr import AICaptchaOCR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="验证码图片路径")
    parser.add_argument(
        "--model",
        default=config.get_setting("ocr_model", "siliconflow:PaddlePaddle/PaddleOCR-VL-1.5", env_name="CEP_OCR_MODEL"),
        help="OCR 模型（支持 provider:model，例如 siliconflow:PaddlePaddle/PaddleOCR-VL-1.5）",
    )
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"错误: 图片文件不存在: {args.image}")
        return

    with open(args.image, "rb") as f:
        img = f.read()

    ocr = AICaptchaOCR(model=args.model)
    if not ocr.enabled():
        print(
            "OCR 未启用：请在 configs/settings.yaml 中配置 api_key 或设置环境变量。"
        )
        return

    text = ocr.recognize(img)
    print(text)


if __name__ == "__main__":
    main()
