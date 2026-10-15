export default function ReleaseNotes({ notes }: { notes: string }) {
  // Simple markdown-like rendering for release notes
  const lines = notes.split('\n');
  const elements: JSX.Element[] = [];
  let listItems: string[] = [];
  let inCode = false;
  let codeLines: string[] = [];

  function flushList() {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`}>
          {listItems.map((item, i) => (
            <li key={i}>{renderInline(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  }

  function flushCode() {
    if (codeLines.length > 0) {
      elements.push(
        <pre key={`code-${elements.length}`} className="code-block">
          {codeLines.join('\n')}
        </pre>
      );
      codeLines = [];
      inCode = false;
    }
  }

  function renderInline(text: string): React.ReactNode {
    // Bold: **text**
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  }

  for (const line of lines) {
    if (line.startsWith('## ')) {
      flushList();
      flushCode();
      elements.push(<h4 key={`h4-${elements.length}`}>{line.slice(3)}</h4>);
    } else if (line.startsWith('### ')) {
      flushList();
      flushCode();
      elements.push(<h5 key={`h5-${elements.length}`}>{line.slice(4)}</h5>);
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      listItems.push(line.slice(2));
    } else if (line.startsWith('```')) {
      if (inCode) {
        flushCode();
      } else {
        flushList();
        inCode = true;
      }
    } else if (inCode) {
      codeLines.push(line);
    } else if (line.trim() === '') {
      flushList();
      elements.push(<div key={`br-${elements.length}`} className="note-spacer" />);
    } else {
      flushList();
      flushCode();
      elements.push(<p key={`p-${elements.length}`}>{renderInline(line)}</p>);
    }
  }
  flushList();
  flushCode();

  return (
    <div className="release-notes">
      <h4>Release Notes</h4>
      <div className="release-notes-content">{elements}</div>
    </div>
  );
}