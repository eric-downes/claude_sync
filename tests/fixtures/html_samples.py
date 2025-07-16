"""HTML samples for testing extractors.

These are based on the real Claude.ai HTML structure we discovered.
"""

# Simplified but realistic projects page HTML
PROJECTS_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Projects - Claude</title></head>
<body>
    <div class="projects-container">
        <!-- DNI Project -->
        <a href="/project/0197d5a6-8f23-7002-9e49-0f72752b214c">
            <div>
                <div>DNI</div>
                <div>EU-only MLETR</div>
                <div>
                    <span>Updated</span>
                    <span>11 days ago</span>
                </div>
            </div>
        </a>
        
        <!-- DLPoS Project -->
        <a href="/project/019800bd-979b-7116-864b-006d88133519">
            <div>
                <div>DLPoS</div>
                <div>
                    <span>Updated</span>
                    <span>3 days ago</span>
                </div>
            </div>
        </a>
        
        <!-- Monoidal Project -->
        <a href="/project/0197f6c0-91e5-715f-a760-ad3393ee0e40">
            <div>
                <div>monoidal</div>
                <div>
                    <span>Updated</span>
                    <span>5 days ago</span>
                </div>
            </div>
        </a>
        
        <!-- Playing God Project -->
        <a href="/project/0197e6dc-870a-72f5-a626-4511305a308b">
            <div>
                <div>Playing God</div>
                <div>create life!</div>
                <div>
                    <span>Updated</span>
                    <span>8 days ago</span>
                </div>
            </div>
        </a>
    </div>
</body>
</html>
"""

# Empty projects page
EMPTY_PROJECTS_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Projects - Claude</title></head>
<body>
    <div class="projects-container">
        <p>No projects yet</p>
    </div>
</body>
</html>
"""

# DNI project page with knowledge files
DNI_PROJECT_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>DNI - Claude</title></head>
<body>
    <div class="project-content">
        <h1>DNI</h1>
        <p>EU-only MLETR</p>
        
        <section>
            <h2>Project knowledge</h2>
            <div class="instructions">Set project instructions</div>
            <div class="optional">Optional</div>
            <div>8% of project capacity used</div>
            <div>Retrieving</div>
            
            <!-- Knowledge files -->
            <div class="file-item">
                Invoice valuation
                489 lines
                TEXT
                <button>Select file</button>
            </div>
            
            <div class="file-item">
                Illiquid pricing
                421 lines
                TEXT
                <button>Select file</button>
            </div>
            
            <div class="file-item">
                legal memo
                169 lines
                TEXT
                <button>Select file</button>
            </div>
            
            <div class="file-item">
                uk domestic
                105 lines
                TEXT
                <button>Select file</button>
            </div>
            
            <div class="file-item">
                traxpay podcast BoE transcript
                155 lines
                TEXT
                <button>Select file</button>
            </div>
            
            <div class="file-item">
                germany trade fi specific
                452 lines
                TEXT
                <button>Select file</button>
            </div>
            
            <div class="file-item">
                Trade Finance Report 2024
                PDF
                <button>Select file</button>
            </div>
        </section>
    </div>
</body>
</html>
"""

# Project page with no knowledge files
EMPTY_PROJECT_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Project - Claude</title></head>
<body>
    <div class="project-content">
        <h1>Test Project</h1>
        <p>A project with no files</p>
        
        <section>
            <h2>Project knowledge</h2>
            <div class="instructions">Set project instructions</div>
            <div class="optional">Optional</div>
            <div>0% of project capacity used</div>
            <p>No files added yet</p>
        </section>
    </div>
</body>
</html>
"""

# Login page (for auth checking)
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Login - Claude</title></head>
<body>
    <div class="login-container">
        <h1>Sign in to Claude</h1>
        <button>Continue with Google</button>
    </div>
</body>
</html>
"""