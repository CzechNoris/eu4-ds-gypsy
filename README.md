# DS on EU4

## Preparing files

### General tips

- replace every whitespace line
```regex
^\s*$\n
```

- replace all chars over multiple lines 
```regex
START[\s\S\r]*?END
```

### Transform ideas

- replace tabs with spaces (tab -> 2 spaces)
- remove comments - regex `^\s*#.*$\n`
- remove `ai_will_do` sections (expect correct indentation) - regex `^  ai_will_do[\s\S\r]*?^  \}\n`
- remove `trigger` sections (expect correct indentation) - regex `^  trigger[\s\S\r]*?^  \}\n`
- yamlmization 
    - regex `\s*=\s*\{\s*\n` -> `:\n`
    - regex `\s*=\s*` -> `: `
    - remove regex `^\s*\}\s*$\n$`
- remove empty lines - regex `^\s*\n`

decision = improve_development