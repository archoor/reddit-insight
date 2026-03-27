from datetime import datetime, timezone

from sqlmodel import Session

from app.database import engine
from app.models.post import AnalysisStatus, Post


def _seed_posts():
    with Session(engine) as session:
        p1 = Post(
            reddit_id="r1",
            subreddit_name="alpha",
            title="Hello World",
            score=10,
            num_comments=3,
            analysis_status=AnalysisStatus.PENDING,
            reddit_created_at=datetime.now(timezone.utc),
        )
        p2 = Post(
            reddit_id="r2",
            subreddit_name="beta",
            title="Other Topic",
            score=50,
            num_comments=20,
            analysis_status=AnalysisStatus.DONE,
            reddit_created_at=datetime.now(timezone.utc),
        )
        session.add(p1)
        session.add(p2)
        session.commit()
        session.refresh(p1)
        session.refresh(p2)
        return p1.id, p2.id


def test_list_posts_pagination_and_filters(client):
    id1, id2 = _seed_posts()

    r = client.get("/api/posts")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    r_sub = client.get("/api/posts", params={"subreddit": "alpha"})
    assert r_sub.json()["total"] == 1
    assert r_sub.json()["items"][0]["subreddit_name"] == "alpha"

    r_search = client.get("/api/posts", params={"search": "Hello"})
    assert r_search.json()["total"] == 1

    r_score = client.get("/api/posts", params={"min_score": 40})
    assert r_score.json()["total"] == 1
    assert r_score.json()["items"][0]["id"] == id2

    r_status = client.get("/api/posts", params={"analysis_status": "done"})
    assert r_status.json()["total"] == 1
    assert r_status.json()["items"][0]["id"] == id2

    r_page = client.get("/api/posts", params={"page": 1, "page_size": 1})
    assert r_page.json()["total"] == 2
    assert len(r_page.json()["items"]) == 1


def test_get_post_by_id(client):
    pid, _ = _seed_posts()
    r = client.get(f"/api/posts/{pid}")
    assert r.status_code == 200
    assert r.json()["reddit_id"] == "r1"


def test_get_post_404(client):
    assert client.get("/api/posts/99999").status_code == 404


def test_get_post_comments_empty(client):
    pid, _ = _seed_posts()
    r = client.get(f"/api/posts/{pid}/comments")
    assert r.status_code == 200
    assert r.json() == []


def test_get_post_comments_404(client):
    assert client.get("/api/posts/99999/comments").status_code == 404


def test_trigger_fetch_comments_404(client):
    assert client.post("/api/posts/99999/fetch-comments").status_code == 404
