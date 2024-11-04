# Youtube Transcriptions Catcher

Aplicação web full-stack em Django que permite aos usuários extrair e processar transcrições de vídeos do YouTube de forma eficiente e user-friendly. 
O sistema aceita URLs de vídeos individuais ou canais inteiros, processando-os para gerar arquivos de saída em formato TXT ou JSONL contendo as transcrições e títulos dos vídeos.

## Tecnologias e Arquitetura
- Backend: Python com Django, integrando BeautifulSoup e requests para web scraping, youtube-dl para processamento de vídeo, e ThreadPoolExecutor para concorrência.
- Frontend: HTML5, CSS3 (com flexbox e media queries), e JavaScript vanilla para interatividade.
- Integração: Formulários Django para comunicação entre frontend e backend.

## Funcionalidades Principais
1. Extração de transcrições de vídeos individuais e canais do YouTube.
2. Interface web responsiva e intuitiva para submissão de URLs.
3. Adição dinâmica de campos de URL (até 5) com validação em tempo real.
4. Processamento concorrente de múltiplos vídeos para maior eficiência.
5. Geração de arquivos de saída em formatos TXT e JSONL.
6. Tratamento robusto de erros e logging extensivo.

## Técnicas Avançadas Aplicadas
- Web scraping sofisticado para extração de dados do YouTube.
- Parsing de JSON embutido usando expressões regulares.
- Multithreading para processamento paralelo eficiente.
- Design responsivo com CSS flexbox e media queries.
- Validação de formulários no lado do cliente e servidor.
- Implementação de CSRF protection e outras medidas de segurança.

## Destaques de UX/UI
- Design moderno e acessível com esquema de cores contrastante.
- Feedback visual imediato para ações do usuário e validações.
- Suporte a diferentes tamanhos de tela para uma experiência consistente.
- Interatividade aprimorada com JavaScript para adição/remoção dinâmica de campos.

## Aspectos Técnicos Notáveis:
- Uso de Django para gerenciamento eficiente do backend.
- Implementação de concurrent.futures para processamento assíncrono.
- Integração seamless entre frontend interativo e backend robusto.
- Manipulação avançada de respostas HTTP para download de arquivos.

## Habilidades em desenvolvimento web full-stack:
- Desenvolvimento backend com Python e Django.
- Frontend responsivo e interativo com HTML5, CSS3, e JavaScript.
- Web scraping e automação avançados.
- Processamento assíncrono e manipulação eficiente de dados.
- Design de UI/UX centrado no usuário.
- Práticas de segurança web e otimização de performance.
