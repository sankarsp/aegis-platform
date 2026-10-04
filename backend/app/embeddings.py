"""Text embedders.

BedrockEmbedder calls Amazon Titan Text Embeddings v2 in AWS.
HashEmbedder is a deterministic, offline feature-hashing embedder for local development and tests;
it captures word overlap, not meaning, so use Bedrock for real semantic search.
"""

import hashlib
import json
import math
import re
from functools import lru_cache
from typing import Protocol

from .config import get_settings

_TOKEN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class HashEmbedder:
    def __init__(self, dim: int):
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        toks = _TOKEN.findall(text.lower().replace("_", " ").replace(".", " "))
        feats = list(toks)
        feats += [f"{a}_{b}" for a, b in zip(toks, toks[1:], strict=False)]
        for t in toks:  # character trigrams help with partial matches such as "dob" vs "date of birth"
            padded = f"#{t}#"
            feats += [padded[i : i + 3] for i in range(len(padded) - 2)]
        return feats

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for f in self._features(text):
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
            weight = 1.0 if "_" in f or len(f) > 3 else 0.35
            v[h % self.dim] += weight if (h >> 63) & 1 else -weight
        return _normalize(v)


class BedrockEmbedder:
    def __init__(self, model_id: str, region: str, dim: int):
        import boto3  # imported lazily so local runs do not need AWS credentials

        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._model_id = model_id
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text[:8000], "dimensions": self.dim, "normalize": True})
        resp = self._client.invoke_model(
            modelId=self._model_id, body=body, contentType="application/json", accept="application/json"
        )
        return json.loads(resp["body"].read())["embedding"]


@lru_cache
def get_embedder() -> Embedder:
    s = get_settings()
    if s.embedding_provider == "bedrock":
        return BedrockEmbedder(s.bedrock_embedding_model_id, s.aws_region, s.embedding_dim)
    return HashEmbedder(s.embedding_dim)
