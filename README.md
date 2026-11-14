# Gilbert's BioGas Experts

A responsive biogas information and enquiry website built with HTML templates, CSS, JavaScript, and Python. Contact enquiries are stored in MongoDB.

## Project structure

- `app.py` — Python web server, page assembly, and MongoDB-backed contact form endpoint.
- `templates/index.html` — document shell that includes the individual page sections.
- `templates/sections/` — separate HTML files for the header, hero, about, solutions, process, impact, contact, and footer.
- `templates/pages/` — dedicated Services, Products, Gallery, Blog, and About pages.
- `static/styles.css` — responsive styles and layout.
- `static/images/` — local images served from `/assets/images/`.
- `static/app.js` — mobile navigation and contact form behavior.
- `requirements.txt` — Python MongoDB driver dependency.

## Add your own images

Copy JPG, JPEG, PNG, GIF, or WebP files into `static/images/`. Reference them in
HTML with a path such as `/assets/images/my-photo.jpg`:

```html
<img src="/assets/images/my-photo.jpg" alt="Describe your photo">
```

For a CSS background image, use the same URL:

```css
background-image: url("/assets/images/my-photo.jpg");
```

Images can also be organized into subfolders, for example
`/assets/images/gallery/project-1.webp`. Restarting the server is not required
after adding or replacing an image.

### Add photos to the Gallery page

Copy your photos into `static/images/gallery/`. The Gallery page automatically
shows supported image files in that folder, sorted by filename. The filename
becomes the photo caption and alt text, so use descriptive names such as
`farm-digester.jpg` or `community-project.webp`. JPG, JPEG, PNG, GIF, and WebP
are supported. If the folder has no photos, the existing sample gallery remains
visible.

## Pages

- `/` — Home
- `/services` — Services
- `/products` — Products
- `/gallery` — Gallery
- `/blog` — Blog
- `/about` — About
- `/contact` — Contact and enquiry form

## Run locally

Python 3.10 or newer and a running MongoDB instance are required.

```powershell
python -m pip install -r requirements.txt
$env:MONGODB_URI = "mongodb://localhost:27017"
python app.py
```

Open <http://127.0.0.1:8000> in your browser. Enquiries are saved in the `gilberts_biogas` database's `enquiries` collection by default. Set `MONGODB_URI` to your MongoDB connection string and optionally set `MONGODB_DATABASE` to use a different database. The website can start if MongoDB is temporarily unavailable, but contact submissions return an error until the database can be reached.

## Deploy to Render

Create a Render **Web Service** with the repository root as its root directory,
`pip install -r requirements.txt` as the build command, and `python app.py` as
the start command. The server listens on `0.0.0.0` and uses Render's `PORT`
environment variable.

To enable contact form submissions, add `MONGODB_URI` in the Render service's
environment settings and set it to your MongoDB connection string. If you use
MongoDB Atlas, make sure its network access rules allow connections from
Render. Without a reachable MongoDB instance, the site can still start, but
contact submissions will fail.
