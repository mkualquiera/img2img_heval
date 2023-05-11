import base64
import json
import os
import random
import threading
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


def append_rating(rating_dict):
    with data_lock:
        try:
            with open('data/ratings.json', 'r') as f:
                ratings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            ratings = []
        
        ratings.append(rating_dict)

        with open('data/ratings.json', 'w') as f:
            json.dump(ratings, f)

data_lock = threading.Lock()

def get_common_image_ids(dir_a_path, dir_b_path):
    a_files = os.listdir(dir_a_path)
    b_files = os.listdir(dir_b_path)

    # Extract image IDs (part before the "_")
    a_ids = {file.split("_")[0] for file in a_files}
    b_ids = {file.split("_")[0] for file in b_files}

    # Find the intersection of image IDs
    common_ids = a_ids.intersection(b_ids)

    return common_ids

app = FastAPI()

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Replace this with the path to your images directory
IMAGE_DIR = Path('images')

a_dir = IMAGE_DIR / "a"
b_dir = IMAGE_DIR / "b"

common_image_ids = list(get_common_image_ids(a_dir, b_dir))

print(f"Found {len(common_image_ids)} common image IDs")

class Rating(BaseModel):
    image_id: str
    a_index: int
    b_index: int
    rating_type: str
    choice: str
    tracking_id: str

def load_image(img_path):
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    return base64.b64encode(img_bytes).decode("utf-8")

def pick_rating():
    return random.choice(['Alignment', 'Conditional Preference', 'Unconditional Preference'])

@app.get("/get_prompt")
def get_prompt():
    image_id = random.choice(list(common_image_ids))
    rating_type = pick_rating()
    a_index = random.randint(0, 3)
    b_index = random.randint(0, 3)
    try:
        original_img = load_image(IMAGE_DIR / "original" / f"{image_id}.jpg")
        a_img = load_image(IMAGE_DIR / "a" / f"{image_id}_{a_index}.jpg")
        b_img = load_image(IMAGE_DIR / "b" / f"{image_id}_{b_index}.jpg")
    except FileNotFoundError:
        # Print stack
        import traceback
        traceback.print_exc()
        print(f"Image file missing for image ID {image_id}")
        print(f"Original: {IMAGE_DIR / 'original' / f'{image_id}.jpg'}")
        print(f"A: {IMAGE_DIR / 'a' / f'{image_id}_{a_index}.jpg'}")
        print(f"B: {IMAGE_DIR / 'b' / f'{image_id}_{b_index}.jpg'}")
        raise HTTPException(status_code=404, detail="Image file missing")

    return {
        "rating_type": rating_type,
        "image_id": str(image_id),
        "original": original_img,
        "a": a_img,
        "b": b_img,
        "a_index": a_index,
        "b_index": b_index
    }

@app.post("/rating")
def save_rating(rating: Rating):

    rating_dict = rating.dict()
    # dump as json to /app/data
    append_rating(rating_dict)

    return JSONResponse(status_code=200, content={"message": "Rating saved"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="192.168.0.105", port=8000)