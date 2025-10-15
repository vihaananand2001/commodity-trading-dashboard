#!/bin/bash

# Setup script for GitHub repository and Streamlit Cloud deployment

echo "🚀 Setting up GitHub repository for Streamlit Cloud deployment..."

# Initialize git repository if not already done
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
fi

# Create .gitignore
cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Data files (optional - remove if you want to include data)
data/raw/
*.csv
*.xlsx
*.xls

# Model files (optional - remove if you want to include models)
models/*.csv
models/*.txt

# Temporary files
temp/
tmp/
*.tmp

# Streamlit
.streamlit/secrets.toml
EOF

echo "✅ Created .gitignore"

# Add all files to git
echo "📝 Adding files to git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: Commodity Trading Dashboard with Streamlit"

echo ""
echo "🎉 Repository setup complete!"
echo ""
echo "📋 Next steps for Streamlit Cloud deployment:"
echo "1. Create a new repository on GitHub"
echo "2. Push your code to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Go to https://share.streamlit.io/"
echo "4. Click 'New app' and connect your GitHub repository"
echo "5. Set the main file path to: streamlit_dashboard.py"
echo "6. Deploy!"
echo ""
echo "🌐 Your Streamlit app will be available at:"
echo "   https://YOUR_USERNAME-YOUR_REPO_NAME.streamlit.app"
