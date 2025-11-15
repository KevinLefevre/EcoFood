from __future__ import annotations

from typing import Any, Dict, List


def household_profile(members: List[Dict[str, Any]]) -> Dict[str, Any]:
  """
  Normalize a household description into a compact profile.

  Expected member shape:
  {
    "name": str,
    "role": "Adult" | "Child" | "Guest" | str,
    "allergens": [str],
    "likes": [str]
  }
  """

  unique_allergens: Dict[str, int] = {}
  like_counts: Dict[str, int] = {}
  roles: Dict[str, int] = {}

  for member in members:
    for allergen in member.get("allergens", []):
      key = allergen.strip().lower()
      if not key:
        continue
      unique_allergens[key] = unique_allergens.get(key, 0) + 1

    for like in member.get("likes", []):
      key = like.strip().lower()
      if not key:
        continue
      like_counts[key] = like_counts.get(key, 0) + 1

    role = str(member.get("role", "Unknown")).strip()
    if role:
      roles[role] = roles.get(role, 0) + 1

  sorted_allergens = sorted(unique_allergens.items(), key=lambda kv: (-kv[1], kv[0]))
  sorted_likes = sorted(like_counts.items(), key=lambda kv: (-kv[1], kv[0]))

  return {
    "member_count": len(members),
    "roles": roles,
    "allergens": [{"name": k, "count": v} for k, v in sorted_allergens],
    "top_likes": [{"name": k, "count": v} for k, v in sorted_likes[:10]],
  }


TOOLS: Dict[str, Any] = {
  "household.profile": household_profile,
}

