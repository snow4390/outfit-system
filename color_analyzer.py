from PIL import Image
import numpy as np
import colorsys


def rgb_to_hsv_360(rgb):
    r, g, b = [x / 255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return round(h * 360, 2), round(s, 4), round(v, 4)


def is_neutral_color(rgb, sat_threshold=0.18, dark_threshold=0.20, light_threshold=0.88):
    _, s, v = rgb_to_hsv_360(rgb)
    if s <= sat_threshold:
        return True
    if v <= dark_threshold or v >= light_threshold:
        return True
    return False


def simple_kmeans(pixels, k=3, max_iter=20, seed=42):
    if len(pixels) == 0:
        return []

    if len(pixels) < k:
        return pixels.tolist()

    rng = np.random.default_rng(seed)
    centroids = pixels[rng.choice(len(pixels), size=k, replace=False)].astype(np.float32)

    for _ in range(max_iter):
        distances = np.linalg.norm(pixels[:, None] - centroids[None, :], axis=2)
        labels = np.argmin(distances, axis=1)

        new_centroids = []
        for i in range(k):
            cluster_points = pixels[labels == i]
            if len(cluster_points) == 0:
                new_centroids.append(centroids[i])
            else:
                new_centroids.append(cluster_points.mean(axis=0))

        new_centroids = np.array(new_centroids, dtype=np.float32)

        if np.allclose(centroids, new_centroids, atol=1.0):
            break

        centroids = new_centroids

    # 依照群集大小排序，最大群在前面，讓 main_rgb 更穩
    distances = np.linalg.norm(pixels[:, None] - centroids[None, :], axis=2)
    labels = np.argmin(distances, axis=1)
    counts = [(i, np.sum(labels == i)) for i in range(len(centroids))]
    counts.sort(key=lambda x: x[1], reverse=True)

    ordered_centroids = [centroids[i] for i, _ in counts]
    return np.clip(np.array(ordered_centroids).astype(int), 0, 255).tolist()


def remove_near_white_background(pixels, threshold=245):
    mask = np.any(pixels < threshold, axis=1)
    filtered = pixels[mask]
    if len(filtered) == 0:
        return pixels
    return filtered


def remove_near_black_noise(pixels, threshold=10):
    mask = np.any(pixels > threshold, axis=1)
    filtered = pixels[mask]
    if len(filtered) == 0:
        return pixels
    return filtered


def get_warm_cool_label(h, s):
    if s < 0.10:
        return "neutral"

    # 暖色：紅橘黃
    if (0 <= h < 90) or (330 <= h <= 360):
        return "warm"

    # 冷色：綠藍紫
    return "cool"


def extract_color_features(image_path, k=3, resize=(200, 200)):
    image = Image.open(image_path).convert("RGB")
    image = image.resize(resize)

    pixels = np.array(image).reshape(-1, 3)
    pixels = remove_near_white_background(pixels)
    pixels = remove_near_black_noise(pixels)

    palette_rgb = simple_kmeans(pixels, k=k)
    if not palette_rgb:
        palette_rgb = [[128, 128, 128]]

    main_rgb = palette_rgb[0]
    main_hsv = rgb_to_hsv_360(main_rgb)
    palette_hsv = [rgb_to_hsv_360(c) for c in palette_rgb]

    h, s, v = main_hsv
    warm_cool = get_warm_cool_label(h, s)

    return {
        "palette_rgb": palette_rgb,
        "palette_hsv": palette_hsv,
        "main_rgb": main_rgb,
        "main_hsv": main_hsv,
        "is_neutral": is_neutral_color(main_rgb),
        "brightness": v,
        "saturation": s,
        "warm_cool": warm_cool
    }