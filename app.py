from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
import html
import json
import logging
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlparse

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError


ROOT = Path(__file__).resolve().parent
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8000))
SECTIONS = ("header", "hero", "about", "solutions", "process", "impact", "contact", "footer")
PAGE_TITLES = {
    "home": "Gilbert's BioGas Experts | Good energy, naturally",
    "services": "Our Services | Gilbert's BioGas Experts",
    "products": "Biogas Products | Gilbert's BioGas Experts",
    "gallery": "Project Gallery | Gilbert's BioGas Experts",
    "blog": "Biogas Journal | Gilbert's BioGas Experts",
    "about": "About Us | Gilbert's BioGas Experts",
    "contact": "Contact Us | Gilbert's BioGas Experts",
}
PAGE_DESCRIPTIONS = {
    "home": "Gilbert's BioGas Experts helps homes, farms and businesses turn organic waste into clean, dependable energy.",
    "services": "Explore biogas consultation, system design, installation guidance, and ongoing support.",
    "products": "Explore practical biogas systems and equipment for homes, farms, and businesses.",
    "gallery": "See biogas solutions, renewable energy systems, and circular farming in action.",
    "blog": "Ideas and practical guides to biogas, organic waste, and renewable energy.",
    "about": "Meet Gilbert's BioGas Experts and learn about our practical, sustainable approach to biogas.",
    "contact": "Contact Gilbert's BioGas Experts to discuss biogas system repairs, planning, and support.",
}
PAGE_PATHS = {
    "/": "home",
    "/services": "services",
    "/products": "products",
    "/gallery": "gallery",
    "/blog": "blog",
    "/about": "about",
    "/contact": "contact",
}
MAX_REQUEST_SIZE = 16_384
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "gilberts_biogas")
MONGODB_COLLECTION = "enquiries"
IMAGE_CONTENT_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
mongo_client = None
enquiries_collection: Collection | None = None


def initialize_database():
    global enquiries_collection, mongo_client

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5_000)
    mongo_client = client
    enquiries_collection = client[MONGODB_DATABASE][MONGODB_COLLECTION]
    try:
        client.admin.command("ping")
    except PyMongoError as error:
        logging.warning(
            "MongoDB is unavailable. The website will run, but contact submissions "
            "will fail until the database is reachable: %s",
            error,
        )


class BiogasRequestHandler(BaseHTTPRequestHandler):
    def send_content(self, status, content, content_type):
        encoded_content = content.encode("utf-8")
        self.send_bytes(status, encoded_content, content_type)

    def send_bytes(self, status, content, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def serve_image(self, path):
        image_name = unquote(path.removeprefix("/assets/images/"))
        image_parts = image_name.split("/")
        if (
            not image_name
            or "\\" in image_name
            or ":" in image_name
            or any(part in {"", ".", ".."} for part in image_parts)
        ):
            return False

        content_type = IMAGE_CONTENT_TYPES.get(Path(image_name).suffix.lower())
        if content_type is None:
            return False

        image_root = (ROOT / "static" / "images").resolve()
        try:
            image_path = (image_root / image_name).resolve(strict=True)
        except FileNotFoundError:
            return False
        except (OSError, ValueError):
            logging.exception("Unable to resolve local image %s.", image_name)
            self.send_content(500, "Unable to read image", "text/plain; charset=utf-8")
            return True

        try:
            image_path.relative_to(image_root)
        except ValueError:
            return False

        try:
            if not image_path.is_file():
                return False
            image_content = image_path.read_bytes()
        except (OSError, ValueError):
            logging.exception("Unable to read local image %s.", image_name)
            self.send_content(500, "Unable to read image", "text/plain; charset=utf-8")
            return True

        self.send_bytes(200, image_content, content_type)
        return True

    def send_json(self, status, payload):
        self.send_content(status, json.dumps(payload), "application/json; charset=utf-8")

    def render_gallery_items(self):
        gallery_root = ROOT / "static" / "images" / "gallery"
        image_paths = sorted(
            (
                path
                for path in gallery_root.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_CONTENT_TYPES
            ),
            key=lambda path: path.name.casefold(),
        )
        if not image_paths:
            return ""

        items = []
        for index, image_path in enumerate(image_paths, start=1):
            title = re.sub(r"[-_]+", " ", image_path.stem).strip().title()
            escaped_title = html.escape(title, quote=True)
            image_url = quote(image_path.name, safe="")
            items.append(
                f'<figure class="gallery-item{" gallery-item-wide" if index == 1 else ""}">'
                f'<img src="/assets/images/gallery/{image_url}" alt="{escaped_title}">'
                f'<figcaption><span>{index:02} / GALLERY</span>'
                f"<strong>{escaped_title}</strong></figcaption></figure>"
            )
        return "\n".join(items)

    def render_page(self, page_name):
        page = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        page_content = (ROOT / "templates" / "sections" / "hero.html").read_text(
            encoding="utf-8"
        ) if page_name == "home" else (ROOT / "templates" / "pages" / f"{page_name}.html").read_text(
            encoding="utf-8"
        )

        if page_name == "home":
            for section in SECTIONS[2:-1]:
                section_html = (
                    ROOT / "templates" / "sections" / f"{section}.html"
                ).read_text(encoding="utf-8")
                page_content += section_html

        if page_name == "gallery":
            gallery_items = self.render_gallery_items()
            if gallery_items:
                page_content = page_content.replace("<!-- GALLERY_ITEMS -->", gallery_items)
                page_content = re.sub(
                    r"\s*<!-- GALLERY_FALLBACK_START -->.*?<!-- GALLERY_FALLBACK_END -->",
                    "",
                    page_content,
                    flags=re.DOTALL,
                )
            else:
                page_content = page_content.replace("<!-- GALLERY_ITEMS -->", "")
                page_content = page_content.replace("<!-- GALLERY_FALLBACK_START -->", "")
                page_content = page_content.replace("<!-- GALLERY_FALLBACK_END -->", "")

        if page_name == "contact":
            contact_section = (ROOT / "templates" / "sections" / "contact.html").read_text(
                encoding="utf-8"
            )
            page_content = page_content.replace("<!-- CONTACT_FORM -->", contact_section)

        for section in ("header", "footer"):
            section_html = (ROOT / "templates" / "sections" / f"{section}.html").read_text(
                encoding="utf-8"
            )
            if section == "header":
                section_html = section_html.replace(
                    f'data-page="{page_name}"', 'aria-current="page"'
                )
            page = page.replace(f"<!-- SECTION: {section} -->", section_html)

        return (
            page.replace("<!-- PAGE_TITLE -->", PAGE_TITLES[page_name])
            .replace("<!-- PAGE_DESCRIPTION -->", PAGE_DESCRIPTIONS[page_name])
            .replace("<!-- PAGE_CONTENT -->", page_content)
        )

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path in PAGE_PATHS:
            page_name = PAGE_PATHS[path]
            self.send_content(200, self.render_page(page_name), "text/html; charset=utf-8")
            return

        if path.startswith("/assets/images/") and self.serve_image(path):
            return

        assets = {
            "/assets/styles.css": ("static/styles.css", "text/css; charset=utf-8"),
            "/assets/app.js": ("static/app.js", "text/javascript; charset=utf-8"),
        }
        asset = assets.get(path)
        if asset:
            asset_path = ROOT / asset[0]
            self.send_content(200, asset_path.read_text(encoding="utf-8"), asset[1])
            return

        self.send_content(404, "Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if urlparse(self.path).path != "/api/contact":
            self.send_json(404, {"error": "Not found."})
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None or not content_length.isascii() or not content_length.isdigit():
            self.send_json(400, {"error": "A valid request body is required."})
            return

        if len(content_length) > 8 or int(content_length) > MAX_REQUEST_SIZE:
            self.send_json(413, {"error": "The message is too large."})
            return

        try:
            form = json.loads(self.rfile.read(int(content_length)))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Please send a valid JSON message."})
            return

        if not isinstance(form, dict):
            self.send_json(400, {"error": "Please check the form and try again."})
            return

        name = form.get("name", "").strip() if isinstance(form.get("name"), str) else ""
        email = form.get("email", "").strip() if isinstance(form.get("email"), str) else ""
        message = form.get("message", "").strip() if isinstance(form.get("message"), str) else ""

        if not name or len(name) > 100:
            self.send_json(400, {"error": "Enter your name (up to 100 characters)."})
            return
        if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            self.send_json(400, {"error": "Enter a valid email address."})
            return
        if not message or len(message) > 5_000:
            self.send_json(400, {"error": "Enter a message of up to 5,000 characters."})
            return

        if enquiries_collection is None:
            logging.error("Cannot save contact enquiry because MongoDB is not initialized.")
            self.send_json(503, {"error": "Messages are temporarily unavailable. Please try again later."})
            return

        try:
            enquiries_collection.insert_one(
                {
                    "name": name,
                    "email": email,
                    "message": message,
                    "created_at": datetime.now(timezone.utc),
                }
            )
        except PyMongoError:
            logging.exception("Unable to save contact enquiry to MongoDB.")
            self.send_json(503, {"error": "We couldn't save your message right now. Please try again later."})
            return

        self.send_json(201, {"message": "Thanks for reaching out. Your message has been received."})

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    initialize_database()
    port = int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer(("0.0.0.0", port), BiogasRequestHandler)
    print(f"Gilbert's BioGas Experts is running on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
        if mongo_client:
            mongo_client.close()