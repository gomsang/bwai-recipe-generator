import os, uuid, json, mimetypes, logging
from pathlib import Path
from flask import Flask, request, render_template, url_for
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ───────────────────────────────────────────────
# 환경 변수 로드
# ───────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")

INGREDIENTS_MODEL_NAME = os.getenv("INGREDIENTS_MODEL_NAME", "gemini-2.5-flash-preview-04-17")
RECIPE_MODEL_NAME      = os.getenv("RECIPE_MODEL_NAME", "gemini-2.5-flash-preview-04-17")
IMAGE_MODEL_NAME       = os.getenv("IMAGE_MODEL_NAME", "gemini-2.0-flash-exp-image-generation")

# ───────────────────────────────────────────────
# 경로 설정
# ───────────────────────────────────────────────
BASE    = Path(__file__).parent
PROMPTS = BASE / "prompts"
STATIC  = BASE / "static"
IMAGES  = STATIC / "images"          # 업로드·생성된 이미지 전용 폴더

ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
for p in (PROMPTS, STATIC, IMAGES):
    p.mkdir(parents=True, exist_ok=True)

# ───────────────────────────────────────────────
# Flask
# ───────────────────────────────────────────────
app = Flask(__name__, static_folder=str(STATIC))
app.config['SECRET_KEY'] = os.urandom(24)

# ───────────────────────────────────────────────
# 로깅
# ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# ───────────────────────────────────────────────
# Google Generative AI
# ───────────────────────────────────────────────
genai_client = genai.Client(api_key=API_KEY)

# ───────────────────────────────────────────────
# 유틸리티
# ───────────────────────────────────────────────
def load_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding='utf-8')

def allowed_file(fn: str) -> bool:
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED

def unique_filename(ext: str = '.png') -> str:
    ext = '.' + ext.lstrip('.')
    return f"{uuid.uuid4().hex}{ext}"

def save_binary(folder: Path, data: bytes, filename: str | None = None) -> str:
    """folder 하위에 파일 저장 후 static 기준 상대 경로 반환"""
    filename = filename or unique_filename(Path(folder).suffix)
    path = folder / filename
    path.write_bytes(data)
    log.info("파일 저장: %s", path)
    return f"{path.relative_to(STATIC)}"   # e.g. 'images/xxx.png'

def call_model(model: str, contents: list, cfg: types.GenerateContentConfig):
    try:
        return genai_client.models.generate_content(model=model,
                                                    contents=contents,
                                                    config=cfg)
    except errors.APIError as e:
        log.error("모델 호출 오류(%s): %s", model, e)
        raise

# ───────────────────────────────────────────────
# AI 기능
# ───────────────────────────────────────────────
def generate_ingredients(img: bytes, mime: str) -> str:
    contents = [types.Content(role="user", parts=[
        types.Part(inline_data=types.Blob(data=img, mime_type=mime)),
        types.Part(text=load_prompt("prompt_generate_ingredients.txt"))
    ])]
    cfg = types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.8,
        response_mime_type="application/json"
    )
    res = call_model(INGREDIENTS_MODEL_NAME, contents, cfg).text
    json.loads(res)  # validity check
    return res

def generate_recipe(ing_json: str) -> str:
    prompt = f"{load_prompt('prompt_generate_recipe.txt')}\nInput: {ing_json}"
    cfg = types.GenerateContentConfig(
        temperature=0.7,
        top_p=0.9,
        response_mime_type="application/json"
    )
    res = call_model(RECIPE_MODEL_NAME,
                     [types.Content(role="user", parts=[types.Part(text=prompt)])],
                     cfg).text
    json.loads(res)
    return res

def generate_preview_image(prompt: str) -> str | None:
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    cfg = types.GenerateContentConfig(
        temperature=0.5,
        top_p=0.9,
        response_modalities=["image", "text"],
        response_mime_type="text/plain"
    )
    for chunk in genai_client.models.generate_content_stream(
            model=IMAGE_MODEL_NAME, contents=contents, config=cfg):
        parts = getattr(chunk.candidates[0].content, "parts", [])
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline:
                ext = mimetypes.guess_extension(inline.mime_type) or ".png"
                fn  = unique_filename(ext)
                rel = save_binary(IMAGES, inline.data, fn)
                return rel          # 'images/xxx.png'
    return None

# ───────────────────────────────────────────────
# 스토리 이미지 생성
# ───────────────────────────────────────────────
FONT      = STATIC / "NanumSquareRoundB.ttf"
STORY_W   = 1080
STORY_H   = 1920
CARD_SIZE = 840

def _wrap(text: str, font, max_w: int, draw):
    words, line, lines = text.split(), "", []
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, font) <= max_w:
            line = test
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return lines[:3] if len(lines) <= 3 else lines[:3] + ["…"]

def make_story(img_rel_path: str, title: str, kcal: str, time_: str) -> str:
    bg = Image.new("RGBA", (STORY_W, STORY_H), (255, 255, 255, 255))

    hero_file = STATIC / img_rel_path if img_rel_path else None
    if hero_file and hero_file.exists():
        im = Image.open(hero_file).convert("RGB").resize((STORY_W, STORY_H), Image.LANCZOS)
        im = im.filter(ImageFilter.GaussianBlur(22))
        bg.paste(Image.alpha_composite(im.convert("RGBA"),
                                       Image.new("RGBA", im.size, (0, 0, 0, 120))), (0, 0))

    draw  = ImageDraw.Draw(bg)
    cx, cy = (STORY_W - CARD_SIZE) // 2, 260

    shadow = Image.new("RGBA", (CARD_SIZE, CARD_SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((0, 0, CARD_SIZE, CARD_SIZE),
                                             radius=40, fill=(0, 0, 0, 180))
    bg.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(20)), (cx + 8, cy + 18))

    card = Image.new("RGBA", (CARD_SIZE, CARD_SIZE), (255, 255, 255, 240))
    bg.alpha_composite(card, (cx, cy))

    hero_h = CARD_SIZE - 320
    hy = cy + 40
    if hero_file and hero_file.exists():
        hero = Image.open(hero_file).convert("RGB")
        hero.thumbnail((CARD_SIZE - 80, hero_h), Image.LANCZOS)
        hx = cx + (CARD_SIZE - hero.width) // 2
        mask = Image.new("L", hero.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *hero.size), radius=30, fill=255)
        bg.paste(hero, (hx, hy), mask)

    font_title = ImageFont.truetype(str(FONT), 54) if FONT.exists() else ImageFont.load_default()
    font_meta  = ImageFont.truetype(str(FONT), 42) if FONT.exists() else ImageFont.load_default()

    lines = _wrap(title, font_title, CARD_SIZE - 120, draw)
    ty = hy + (hero.height if hero_file and hero_file.exists() else 0) + 40
    for ln in lines:
        draw.text((cx + (CARD_SIZE - draw.textlength(ln, font_title)) // 2, ty),
                  ln, font=font_title, fill="black")
        ty += 62

    meta = f"칼로리 {kcal}   |   시간 {time_}"
    draw.text((cx + (CARD_SIZE - draw.textlength(meta, font_meta)) // 2, ty + 12),
              meta, font=font_meta, fill="#333")

    logo = STATIC / "logo.png"
    if logo.exists():
        lg = Image.open(logo).convert("RGBA")
        lg.thumbnail((480, 240), Image.LANCZOS)
        bg.alpha_composite(lg, ((STORY_W - lg.width) // 2, STORY_H - lg.height - 90))

    fname = unique_filename(".jpg")
    rel   = f"images/{fname}"
    bg.convert("RGB").save(IMAGES / fname, "JPEG", quality=92)
    return rel

# ───────────────────────────────────────────────
# 라우트
# ───────────────────────────────────────────────
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def handle_generation():
    f = request.files.get("image")
    if not f or f.filename == '':
        return render_template("results.html", error="이미지 파일이 없습니다.")
    if not allowed_file(f.filename):
        return render_template("results.html", error="허용되지 않은 파일 형식입니다.")

    mime = f.mimetype or mimetypes.guess_type(f.filename)[0]
    if not mime or not mime.startswith("image/"):
        return render_template("results.html", error="이미지 형식을 인식할 수 없습니다.")

    try:
        img_data   = f.read()
        ing_json   = generate_ingredients(img_data, mime)
        ingredients = json.loads(ing_json)

        recipe_json = generate_recipe(ing_json)
        recipe      = json.loads(recipe_json)

        img_file, img_err = None, None
        prompt = recipe.get("preview_image_prompt")
        if prompt:
            try:
                img_file = generate_preview_image(prompt)
            except Exception as e:
                img_err = str(e)

        return render_template("results.html",
                               ingredients=ingredients,
                               ingredients_json=ing_json,
                               recipe_data=recipe,
                               image_filename=img_file,
                               image_generation_error=img_err)
    except Exception:
        log.exception("처리 오류")
        return render_template("results.html", error="처리 중 오류가 발생했습니다.")

@app.route('/share-image', methods=['POST'])
def share_image():
    data = request.get_json(force=True, silent=True) or {}
    try:
        fn = make_story(data.get("img", "").replace("/static/", ""),
                        data.get("title", "AI 레시피"),
                        data.get("kcal",  "-"),
                        data.get("time",  "-"))
        return {"url": url_for("static", filename=fn)}, 200
    except Exception:
        log.exception("스토리 이미지 생성 실패")
        return {"error": "이미지 생성 실패"}, 500

# ───────────────────────────────────────────────
# 실행
# ───────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)