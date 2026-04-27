from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def sort_centers_by_distance(centers, user_lat, user_lon):
    results = []
    for center in centers:
        dist = haversine(user_lat, user_lon, center.latitude, center.longitude)
        results.append((center, round(dist, 2)))
    results.sort(key=lambda x: x[1])
    return results