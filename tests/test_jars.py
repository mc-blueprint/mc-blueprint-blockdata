import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from mcblockdata import jars


def test_download_server_jar_verifies_and_reuses_cache(tmp_path, monkeypatch):
    content = b"official server jar"
    sha1 = hashlib.sha1(content).hexdigest()
    manifest = {"versions": [{"id": "1.21.11", "url": "https://example.test/version.json"}]}
    metadata = {"downloads": {"server": {"url": "https://example.test/server.jar", "sha1": sha1}}}
    monkeypatch.setattr(
        jars, "_fetch_json", lambda url: manifest if "manifest" in url else metadata
    )
    calls = []

    def download(url, destination):
        calls.append(url)
        destination.write_bytes(content)

    monkeypatch.setattr(jars.urllib.request, "urlretrieve", download)

    path = jars.download_server_jar("1.21.11", tmp_path)
    assert path.read_bytes() == content
    assert jars.download_server_jar("1.21.11", tmp_path) == path
    assert calls == ["https://example.test/server.jar"]


def test_download_server_jar_rejects_invalid_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(
        jars,
        "_fetch_json",
        lambda url: {"versions": [{"id": "1.21.11", "url": "meta"}]}
        if "manifest" in url
        else {"downloads": {"server": {"url": "jar", "sha1": "bad"}}},
    )
    monkeypatch.setattr(
        jars.urllib.request, "urlretrieve", lambda url, path: path.write_bytes(b"bad")
    )

    with pytest.raises(ValueError, match="SHA-1"):
        jars.download_server_jar("1.21.11", tmp_path)

    assert not (tmp_path / "server-1.21.11.jar").exists()
    assert not list(tmp_path.iterdir())


def test_download_client_jar_uses_client_manifest_entry(tmp_path, monkeypatch):
    content = b"official client jar"
    sha1 = hashlib.sha1(content).hexdigest()
    monkeypatch.setattr(
        jars,
        "_fetch_json",
        lambda url: {"versions": [{"id": "1.21.11", "url": "version"}]}
        if "manifest" in url
        else {"downloads": {"client": {"url": "client.jar", "sha1": sha1}}},
    )
    monkeypatch.setattr(
        jars.urllib.request, "urlretrieve", lambda url, path: path.write_bytes(content)
    )

    path = jars.download_client_jar("1.21.11", tmp_path)

    assert path.name == "client-1.21.11.jar"
    assert path.read_bytes() == content


def test_concurrent_downloads_use_independent_temporary_files(tmp_path, monkeypatch):
    content = b"same verified jar"
    barrier = Barrier(2)
    destinations = []
    monkeypatch.setattr(
        jars, "_fetch_json",
        lambda url: {"versions": [{"id": "test", "url": "version"}]}
        if "manifest" in url else {"downloads": {"server": {
            "url": "jar", "sha1": hashlib.sha1(content).hexdigest()
        }}},
    )

    def download(url, path):
        destinations.append(path)
        path.write_bytes(content)
        barrier.wait(timeout=10)

    monkeypatch.setattr(jars.urllib.request, "urlretrieve", download)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: jars.download_server_jar("test", tmp_path), range(2)))
    assert results[0] == results[1]
    assert results[0].read_bytes() == content
    assert len(set(destinations)) == 2
    assert list(tmp_path.iterdir()) == [results[0]]
