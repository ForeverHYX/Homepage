from __future__ import annotations
import re

def parse_education_timeline(raw_markdown: str) -> str:
    """
    Parses the Education section markdown into a timeline HTML.
    
    Expected format per entry:
        - **Institution Name** | date range
          *Role / Degree*
          ![Alt text](/path/to/logo.png)
    
    Returns timeline HTML or falls back to standard markdown rendering.
    """
    import re as _re
    
    lines = raw_markdown.splitlines()
    entries: list[dict] = []
    current_entry: dict | None = None
    
    for line in lines:
        stripped = line.strip()
        
        # New bullet item
        if stripped.startswith("- ") or stripped.startswith("* "):
            if current_entry:
                entries.append(current_entry)
            
            content = stripped[2:].strip()
            
            # Parse: **Institution** | date range
            inst_match = _re.match(r'\*\*(.+?)\*\*\s*\|\s*(.*)', content)
            if inst_match:
                current_entry = {
                    "institution": inst_match.group(1).strip(),
                    "date_range": inst_match.group(2).strip(),
                    "role": "",
                    "logos": [],
                }
            else:
                # Fallback: just bold text without pipe
                bold_match = _re.match(r'\*\*(.+?)\*\*(.*)', content)
                if bold_match:
                    current_entry = {
                        "institution": bold_match.group(1).strip(),
                        "date_range": bold_match.group(2).strip().lstrip("(").rstrip(")").strip(),
                        "role": "",
                        "logos": [],
                    }
                else:
                    current_entry = None
            continue
        
        # Continuation lines (indented)
        if current_entry and stripped:
            # Role: *italic text*
            role_match = _re.match(r'^\*(.+?)\*$', stripped)
            if role_match:
                current_entry["role"] = role_match.group(1).strip()
                continue
            
            # Logo: ![alt](url)
            img_match = _re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
            if img_match:
                for alt, url in img_match:
                    current_entry["logos"].append({"alt": alt, "url": url})
                continue
            
            # Additional description text (not italic, not image)
            if not stripped.startswith("#"):
                if current_entry["role"]:
                    current_entry["role"] += " " + stripped
                else:
                    current_entry["role"] = stripped
    
    # Flush last entry
    if current_entry:
        entries.append(current_entry)
    
    if not entries:
        return ""
    
    # Generate timeline HTML
    html_parts = ['<div class="edu-timeline">']
    for entry in entries:
        is_active = "present" in entry["date_range"].lower()
        active_class = " is-active" if is_active else ""
        
        # Logos
        logos_html = ""
        if entry["logos"]:
            logo_imgs = "".join(
                f'<img src="{logo["url"]}" alt="{logo["alt"]}" class="edu-logo">'
                for logo in entry["logos"]
            )
            logos_html = f'<div class="edu-logo-group">{logo_imgs}</div>'
        
        # Role (support markdown links in role text)
        role_text = entry["role"]
        if role_text:
            # Convert inline markdown links [text](url)
            role_text = _re.sub(
                r'\[([^\]]+)\]\(([^)]+)\)',
                r'<a href="\2" class="link-styled">\1</a>',
                role_text
            )
            # Convert bold
            role_text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', role_text)
            # Convert italic
            role_text = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', role_text)
        
        role_html = f'<p class="edu-role">{role_text}</p>' if role_text else ""
        
        html_parts.append(f'''
            <div class="edu-timeline-item{active_class}">
                <div class="edu-timeline-date">
                    <span>{entry["date_range"]}</span>
                </div>
                <div class="edu-timeline-marker">
                    <div class="edu-timeline-dot"></div>
                </div>
                <div class="edu-timeline-content">
                    <div class="edu-timeline-text">
                        <span class="edu-institution">{entry["institution"]}</span>
                        {role_html}
                    </div>
                    {logos_html}
                </div>
            </div>''')
    
    html_parts.append('</div>')
    return "\n".join(html_parts)
