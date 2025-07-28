# PostgreSQL Setup with PGVector for gabo

This guide will help you set up PostgreSQL with the PGVector extension for the gabo platform.

## Option 1: Docker Setup (Recommended)

### Prerequisites
- Docker and Docker Compose installed

### Quick Start

1. **Start the services:**
   ```bash
   docker-compose up -d
   ```

2. **Verify the services are running:**
   ```bash
   docker-compose ps
   ```

3. **Test the database connection:**
   ```bash
   python scripts/init_database.py --test-only
   ```

4. **Initialize the database:**
   ```bash
   python scripts/init_database.py --init
   ```

### Environment Variables
Copy the example environment file and configure it:
```bash
cp env.example .env
```

Edit `.env` with your configuration:
```bash
# Database Configuration (matches docker-compose.yml)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gabo
DB_USER=gabo_user
DB_PASSWORD=gabo_password

# Add your API keys
EMBEDDING_API_KEY=your_openai_api_key_here
LLM_API_KEY=your_openai_api_key_here
```

## Option 2: Manual PostgreSQL Setup

### Prerequisites
- PostgreSQL 12+ installed
- Ability to install extensions

### Installation Steps

#### Ubuntu/Debian:
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install PGVector
sudo apt install postgresql-16-pgvector
```

#### macOS:
```bash
# Using Homebrew
brew install postgresql
brew install pgvector
```

#### Windows:
Download PostgreSQL from the official website and install PGVector manually.

### Database Setup

1. **Create the database and user:**
   ```sql
   -- Connect as postgres superuser
   sudo -u postgres psql

   -- Create database and user
   CREATE DATABASE gabo;
   CREATE USER gabo_user WITH PASSWORD 'gabo_password';
   GRANT ALL PRIVILEGES ON DATABASE gabo TO gabo_user;
   \q
   ```

2. **Initialize the database:**
   ```bash
   python scripts/init_database.py --init
   ```

## Option 3: Cloud Database Setup

### Using Supabase (Recommended for development)

1. **Create a Supabase project:**
   - Go to https://supabase.com
   - Create a new project
   - Note your database URL and API keys

2. **Enable PGVector:**
   - Go to your Supabase dashboard
   - Navigate to SQL Editor
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

3. **Update environment variables:**
   ```bash
   # Use your Supabase database URL
   DB_HOST=your-project.supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

### Using Neon

1. **Create a Neon project:**
   - Go to https://neon.tech
   - Create a new project
   - Note your connection string

2. **Enable PGVector:**
   - PGVector is enabled by default in Neon

3. **Update environment variables with your Neon connection details**

## Testing Your Setup

### 1. Test Database Connection
```bash
python scripts/init_database.py --test-only
```

Expected output:
```
✅ Connected to PostgreSQL: PostgreSQL 16.x
✅ PGVector extension is available
```

### 2. Initialize Database Tables
```bash
python scripts/init_database.py --init
```

Expected output:
```
✅ Database initialization completed successfully!
```

### 3. Test the Application
```bash
# Start the API server
python -m uvicorn api.upload_endpoint:app --reload

# In another terminal, test the health endpoint
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

#### 1. PGVector Extension Not Available
**Error:** `❌ PGVector extension is not available`

**Solutions:**
- For Docker: Make sure you're using the `pgvector/pgvector:pg16` image
- For manual install: Install the PGVector extension package
- For cloud: Enable the extension in your cloud provider's dashboard

#### 2. Connection Refused
**Error:** `❌ Database connection failed`

**Solutions:**
- Check if PostgreSQL is running: `sudo systemctl status postgresql`
- Verify connection details in your `.env` file
- Check firewall settings

#### 3. Permission Denied
**Error:** `permission denied for database`

**Solutions:**
- Grant proper permissions to the user
- Check if the user exists and has correct privileges

### Verification Commands

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Connect to database manually
psql -h localhost -U gabo_user -d gabo

# Check if PGVector is installed
\dx vector

# List all tables
\dt

# Exit psql
\q
```

## Performance Optimization

### For Production Use

1. **Adjust PostgreSQL settings:**
   ```sql
   -- Increase shared buffers
   ALTER SYSTEM SET shared_buffers = '256MB';
   
   -- Increase work memory
   ALTER SYSTEM SET work_mem = '4MB';
   
   -- Reload configuration
   SELECT pg_reload_conf();
   ```

2. **Optimize vector indexes:**
   ```sql
   -- For better search performance
   CREATE INDEX CONCURRENTLY embeddings_vector_idx_hnsw 
   ON embeddings USING hnsw (embedding vector_cosine_ops);
   ```

3. **Monitor performance:**
   ```sql
   -- Check index usage
   SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
   FROM pg_stat_user_indexes;
   ```

## Next Steps

Once your database is set up:

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis (for task queue):**
   ```bash
   docker-compose up redis -d
   ```

3. **Run the application:**
   ```bash
   python main.py --dev
   ```

4. **Test with a sample file:**
   ```bash
   python main.py --file path/to/your/document.pdf
   ```

Your gabo platform is now ready to process documents and perform semantic search! 