import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models import Base, Video, VideoSnapshot
from dotenv import load_dotenv

def parse_datetime(dt_str):
    # Handle different datetime formats
    try:
        return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        try:
            return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')

def load_json_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def insert_video(db: Session, video_data):
    # Insert video
    video = Video(
        id=video_data['id'],
        creator_id=video_data['creator_id'],
        video_created_at=parse_datetime(video_data['video_created_at']),
        views_count=video_data['views_count'],
        likes_count=video_data.get('likes_count', 0),
        comments_count=video_data.get('comments_count', 0),
        reports_count=video_data.get('reports_count', 0),
        created_at=parse_datetime(video_data['created_at']),
        updated_at=parse_datetime(video_data['updated_at'])
    )
    db.add(video)
    
    # Insert snapshots
    for snapshot_data in video_data.get('snapshots', []):
        snapshot = VideoSnapshot(
            id=snapshot_data['id'],
            video_id=video.id,
            views_count=snapshot_data['views_count'],
            likes_count=snapshot_data.get('likes_count', 0),
            comments_count=snapshot_data.get('comments_count', 0),
            reports_count=snapshot_data.get('reports_count', 0),
            delta_views_count=snapshot_data.get('delta_views_count', 0),
            delta_likes_count=snapshot_data.get('delta_likes_count', 0),
            delta_comments_count=snapshot_data.get('delta_comments_count', 0),
            delta_reports_count=snapshot_data.get('delta_reports_count', 0),
            created_at=parse_datetime(snapshot_data['created_at']),
            updated_at=parse_datetime(snapshot_data['updated_at'])
        )
        db.add(snapshot)
    
    return video

def main():
    # Load environment variables
    load_dotenv()
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Clear existing data
        print("Clearing existing data...")
        db.execute(text("TRUNCATE TABLE video_snapshots CASCADE"))
        db.execute(text("TRUNCATE TABLE videos CASCADE"))
        db.commit()
        
        # Load and insert data
        print("Loading data from videos.json...")
        data = load_json_data('videos.json')
        total = len(data)
        
        print(f"Inserting {total} videos...")
        for i, video_data in enumerate(data, 1):
            insert_video(db, video_data)
            if i % 100 == 0:
                print(f"Processed {i}/{total} videos...")
                db.commit()
        
        db.commit()
        print("Data loading completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
