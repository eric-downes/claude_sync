#!/usr/bin/env python3
"""Analyze the DOM structure of Claude project cards to fix title extraction."""
import json
from src.chrome.robust_client import RobustChromeClient

def main():
    print("\nAnalyzing Claude Project Card Structure")
    print("=" * 60)
    
    with RobustChromeClient() as client:
        pages = client.get_pages()
        claude_page = None
        
        for page in pages:
            if 'claude.ai' in page.get('url', ''):
                claude_page = page
                break
        
        if not claude_page:
            print("❌ No Claude.ai page found")
            return 1
        
        print("✓ Connected to Claude.ai")
        client.connect_to_page(claude_page)
        
        # Navigate to projects
        print("✓ Navigating to projects page...")
        client.navigate_and_wait("https://claude.ai/projects")
        
        # Analyze project card structure
        print("\n📊 Analyzing project card DOM structure...")
        
        analysis = client.evaluate_expression("""
            JSON.stringify((() => {
                const results = [];
                const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
                
                // Analyze first few project cards
                links.slice(0, 3).forEach((link, index) => {
                    const analysis = {
                        index: index,
                        linkHTML: link.innerHTML.substring(0, 500),
                        linkText: link.textContent.trim(),
                        href: link.href,
                        childrenCount: link.children.length,
                        children: []
                    };
                    
                    // Analyze child elements
                    Array.from(link.children).forEach((child, childIndex) => {
                        analysis.children.push({
                            tagName: child.tagName,
                            className: child.className,
                            text: child.textContent.trim(),
                            hasNestedChildren: child.children.length > 0
                        });
                    });
                    
                    // Look for text nodes directly in the link
                    const textNodes = [];
                    for (let node of link.childNodes) {
                        if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                            textNodes.push(node.textContent.trim());
                        }
                    }
                    analysis.directTextNodes = textNodes;
                    
                    // Try to find title and description by analyzing structure
                    if (link.children.length >= 2) {
                        // Common pattern: first child is title, second is description
                        analysis.possibleTitle = link.children[0].textContent.trim();
                        analysis.possibleDescription = link.children[1].textContent.trim();
                    } else if (link.children.length === 1) {
                        // Single child might contain both
                        const singleChild = link.children[0];
                        if (singleChild.children.length >= 2) {
                            analysis.possibleTitle = singleChild.children[0].textContent.trim();
                            analysis.possibleDescription = singleChild.children[1].textContent.trim();
                        }
                    }
                    
                    results.push(analysis);
                });
                
                return results;
            })())
        """)
        
        print("\n🔍 Analysis Results:")
        print("-" * 60)
        
        for proj in analysis:
            print(f"\nProject {proj['index'] + 1}:")
            print(f"  Full text: {proj['linkText']}")
            print(f"  Children count: {proj['childrenCount']}")
            
            if proj['children']:
                print("  Child elements:")
                for i, child in enumerate(proj['children']):
                    print(f"    {i+1}. <{child['tagName']}> - '{child['text'][:50]}...'")
            
            if proj.get('possibleTitle'):
                print(f"  Possible title: {proj['possibleTitle']}")
            if proj.get('possibleDescription'):
                print(f"  Possible description: {proj['possibleDescription']}")
            
            print(f"  Direct text nodes: {proj.get('directTextNodes', [])}")
        
        # Now let's check for DNI specifically
        print("\n\n🎯 Looking for DNI project structure:")
        
        dni_analysis = client.evaluate_expression("""
            JSON.stringify((() => {
                const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
                const dniLink = links.find(link => 
                    link.textContent.includes('DNI') || 
                    link.textContent.includes('MLETR')
                );
                
                if (!dniLink) return null;
                
                const result = {
                    fullText: dniLink.textContent.trim(),
                    href: dniLink.href,
                    innerHTML: dniLink.innerHTML,
                    structure: []
                };
                
                // Recursively analyze structure
                function analyzeElement(el, depth = 0) {
                    const info = {
                        depth: depth,
                        tag: el.tagName,
                        text: el.textContent.trim(),
                        className: el.className,
                        childCount: el.children.length
                    };
                    
                    // Get direct text content (not from children)
                    let directText = '';
                    for (let node of el.childNodes) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            directText += node.textContent;
                        }
                    }
                    info.directText = directText.trim();
                    
                    result.structure.push(info);
                    
                    // Analyze children
                    Array.from(el.children).forEach(child => {
                        analyzeElement(child, depth + 1);
                    });
                }
                
                analyzeElement(dniLink);
                
                return result;
            })())
        """)
        
        if dni_analysis:
            print(f"\nFound DNI project!")
            print(f"Full text: {dni_analysis['fullText']}")
            print("\nDOM Structure:")
            for elem in dni_analysis['structure']:
                indent = "  " * elem['depth']
                print(f"{indent}<{elem['tag']}> direct: '{elem['directText']}' | full: '{elem['text'][:50]}...'")
    
    return 0

if __name__ == "__main__":
    main()