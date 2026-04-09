"""
Battery R&D Pipeline - PostgreSQL Data Layer
Connects to hosted PostgreSQL database for battery cycling data
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')


class BatteryDatabase:
    """PostgreSQL connection for battery cycling data"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.database_url:
            # Build from components
            self.database_url = (
                f"postgresql://{os.getenv('DB_USER')}:"
                f"{os.getenv('DB_PASS')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME')}"
            )
        
        self.engine = create_engine(self.database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        print(f"✓ Connected to PostgreSQL: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    
    def get_battery_ids(self) -> List[str]:
        """Get all battery IDs in database"""
        query = text("SELECT DISTINCT battery_id FROM battery_cycles ORDER BY battery_id")
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [row[0] for row in result.fetchall()]
    
    def get_battery_data(self, battery_id: str) -> pd.DataFrame:
        """Get all cycle data for a specific battery"""
        query = text("""
            SELECT * FROM battery_cycles 
            WHERE battery_id = :battery_id 
            ORDER BY cycle
        """)
        
        return pd.read_sql(query, self.engine, params={'battery_id': battery_id})
    
    def get_all_batteries(self) -> pd.DataFrame:
        """Get all battery data"""
        query = text("SELECT * FROM battery_cycles ORDER BY battery_id, cycle")
        return pd.read_sql(query, self.engine)
    
    def get_cycle_features(self, battery_id: str, cycle: int) -> Dict:
        """Get feature vector for a specific battery at a specific cycle"""
        query = text("""
            SELECT * FROM battery_cycles 
            WHERE battery_id = :battery_id AND cycle = :cycle
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'battery_id': battery_id, 'cycle': cycle})
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
    
    def get_training_data(self, test_ratio: float = 0.2, seed: int = 42) -> tuple:
        """
        Get train/test split by battery ID
        
        Returns:
            (train_df, test_df) - Split by battery (not by cycle)
        """
        import numpy as np
        
        # Get all battery IDs
        battery_ids = self.get_battery_ids()
        
        # Shuffle with seed
        np.random.seed(seed)
        np.random.shuffle(battery_ids)
        
        # Split
        split_idx = int(len(battery_ids) * (1 - test_ratio))
        train_ids = battery_ids[:split_idx]
        test_ids = battery_ids[split_idx:]
        
        # Get data
        train_df = self.get_all_batteries()
        train_df = train_df[train_df['battery_id'].isin(train_ids)]
        
        test_df = self.get_all_batteries()
        test_df = test_df[test_df['battery_id'].isin(test_ids)]
        
        print(f"Train: {len(train_df)} cycles from {len(train_ids)} batteries")
        print(f"Test: {len(test_df)} cycles from {len(test_ids)} batteries")
        
        return train_df, test_df
    
    def get_schema_info(self) -> Dict:
        """Get database schema information"""
        query = text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'battery_cycles'
            ORDER BY ordinal_position
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            columns = [dict(row._mapping) for row in result.fetchall()]
        
        # Get row count
        count_query = text("SELECT COUNT(*) as count FROM battery_cycles")
        with self.engine.connect() as conn:
            result = conn.execute(count_query)
            count = result.fetchone()[0]
        
        return {
            'columns': columns,
            'total_rows': count,
            'battery_count': len(self.get_battery_ids())
        }
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT NOW()"))
                now = result.fetchone()[0]
                print(f"✓ Database connection successful (server time: {now})")
                return True
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False


# Convenience functions
def load_battery_data():
    """Load all battery data from PostgreSQL"""
    db = BatteryDatabase()
    return db.get_all_batteries()


def get_train_test_split(test_ratio=0.2):
    """Get train/test split"""
    db = BatteryDatabase()
    return db.get_training_data(test_ratio=test_ratio)


if __name__ == '__main__':
    # Test connection
    db = BatteryDatabase()
    
    if db.test_connection():
        # Show schema info
        schema = db.get_schema_info()
        print(f"\nDatabase Schema:")
        print(f"  Total rows: {schema['total_rows']}")
        print(f"  Battery count: {schema['battery_count']}")
        print(f"  Columns:")
        for col in schema['columns']:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"    - {col['column_name']}: {col['data_type']} ({nullable})")
