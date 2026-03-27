from datetime import datetime, timezone

from sqlmodel import Session

from app.database import engine
from app.models.post import AnalysisStatus, Post


def test_stats_overview_empty(client):
    r = client.get("/api/stats/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total_posts"] == 0
    assert data["total_comments"] == 0
    assert data["total_subreddits"] == 0
    assert data["total_tasks"] == 0
    assert data["analysis_status_distribution"][AnalysisStatus.PENDING] == 0
    assert data["recent_posts"] == []


def test_stats_overview_with_post(client):
    with Session(engine) as session:
        session.add(
            Post(
                reddit_id="s1",
                subreddit_name="stats_sub",
                title="Stats Title",
                score=1,
                num_comments=0,
                analysis_status=AnalysisStatus.PENDING,
                reddit_created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    r = client.get("/api/stats/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total_posts"] == 1
    assert data["analysis_status_distribution"][AnalysisStatus.PENDING] == 1
    assert len(data["recent_posts"]) == 1
    assert data["posts_by_subreddit"][0]["subreddit"] == "stats_sub"
    assert data["posts_by_subreddit"][0]["count"] == 1
