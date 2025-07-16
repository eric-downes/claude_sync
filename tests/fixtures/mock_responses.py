"""
Mock responses for testing Chrome interactions.
"""

# Mock response for modern Claude UI with card-based projects
MOCK_CLAUDE_PROJECTS_PAGE = {
    "result": {
        "value": """
        (() => {
            // Find all clickable elements that contain "Updated X ago"
            const cards = Array.from(document.querySelectorAll('*'))
                .filter(el => {
                    const style = window.getComputedStyle(el);
                    return style.cursor === 'pointer' &&
                           el.textContent.includes('Updated') &&
                           el.textContent.includes('ago');
                });

            const projects = [];

            // Simulate the real projects we found
            const mockProjects = [
                {
                    text: "DLPoS Updated 2 days ago",
                    name: "DLPoS",
                    description: "",
                    updated: "2 days ago"
                },
                {
                    text: "monoidal Updated 4 days ago",
                    name: "monoidal",
                    description: "",
                    updated: "4 days ago"
                },
                {
                    text: "Playing God create life! Updated 1 week ago",
                    name: "Playing God",
                    description: "create life!",
                    updated: "1 week ago"
                },
                {
                    text: "DNI EU-only MLETR Updated 2 weeks ago",
                    name: "DNI",
                    description: "EU-only MLETR",
                    updated: "2 weeks ago"
                }
            ];

            return mockProjects.map(p => ({
                name: p.name,
                description: p.description,
                updated: "Updated " + p.updated,
                id: 'proj-' + p.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
                url: 'https://claude.ai/project/proj-' + p.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')
            }));
        })()
        """
    }
}

# Response when checking if projects page is loaded
MOCK_PROJECTS_LOADED_CHECK_TRUE = {
    "result": {
        "value": True
    }
}

MOCK_PROJECTS_LOADED_CHECK_FALSE = {
    "result": {
        "value": False
    }
}

# Response for current URL check
MOCK_CURRENT_URL_PROJECTS = {
    "result": {
        "value": "https://claude.ai/projects"
    }
}

MOCK_CURRENT_URL_OTHER = {
    "result": {
        "value": "https://claude.ai/chat/123"
    }
}

# Response for navigation
MOCK_NAVIGATION_SUCCESS = {
    "frameId": "123"
}

# Empty projects response
MOCK_EMPTY_PROJECTS = {
    "result": {
        "value": []
    }
}

# Complex project response (like what we actually see)
MOCK_COMPLEX_PROJECTS = {
    "result": {
        "value": [
            {
                "name": "Cat ProjPlanes (was tmp pp)- projective space cohomology",
                "description": "- difference between two kinds of conics in NDPPs",
                "updated": "Updated 22 days ago",
                "id": "proj-cat-projplanes-was-tmp-pp-projective-space-cohomology",
                "url": "https://claude.ai/project/proj-cat-projplanes-was-tmp-pp-projective-space-cohomology"
            },
            {
                "name": "Information CohomologyCohomology cocycles are not trivial.",
                "description": "the first couple are straightforward, but higher differentials have interesting forms",
                "updated": "Updated 2 months ago",
                "id": "proj-information-cohomologycohomology-cocycles-are-not-trivial",
                "url": "https://claude.ai/project/proj-information-cohomologycohomology-cocycles-are-not-trivial"
            }
        ]
    }
}
