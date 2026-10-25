# Decisões

<!-- project-docs: só o que vale agora. Próximo ID: D-011 · Próximo fato: F-007 -->

## Decisões

### D-001 Formato de extensão do Blender 4.2+
Decisão: o add-on é uma extensão (`fofuxo_modeling_tools/blender_manifest.toml`, id `fofuxo_modeling_tools`, mínimo 4.2), distribuída como zip gerado por `blender --command extension build`. Licença GPL-3.0-or-later.
Por quê: é o formato atual do Blender e o que o usuário instala arrastando o zip.
Origem: sugestão da IA aceita

### D-002 Nomes em inglês com tradução pt-BR registrada
Decisão: nomes de sockets, painéis e operadores ficam em inglês no código; o add-on registra traduções pt_BR (`bpy.app.translations`) para os que o Blender não traduz sozinho.
Por quê: o usuário usa o Blender em português e quer os nomes certos no painel; o código segue em inglês.
Origem: usuário (nomes dos painéis e opções); tradução registrada: sugestão da IA aceita
Afeta: arabesque.py (`TRANSLATIONS`)

### D-003 Modificadores no submenu Add Modifier > Fofuxo
Decisão: os operadores que adicionam modificadores ficam num submenu Fofuxo no fim do Add Modifier, nada no painel N.
Por quê: o usuário não achou os itens no fim de Generate e recusou a aba no painel N.
Origem: usuário

### D-004 Mirror a 45° é um subpainel do Mirror nativo
Decisão: subpainel "Angle" filho de `MOD_PT_Mirror`, com um botão de operador desenhado como checkbox; ligar cria um empty oculto, filho do objeto, girado 45° em Z, como Mirror Object.
Por quê: o usuário quer a opção dentro do Mirror existente; modificadores não aceitam propriedades Python (F-002).
Origem: usuário
Não escolhido: operador com painel N - recusado; Geometry Nodes - perde clipping, merge e espelhamento de UV do Mirror nativo.

### D-005 Node groups versionados e atualizados ao abrir o arquivo
Decisão: cada node group do add-on leva uma custom property com o número da versão; ao abrir o arquivo (load_post) ou ativar o add-on (timer), o grupo antigo é atualizado no lugar, e os valores dos modificadores são levados pelo nome do input (`RENAMED_INPUTS` para renomeados).
Por quê: o grupo fica salvo no .blend; sem isso, reinstalar o add-on não mudava nada no arquivo do usuário.
Origem: sugestão da IA aceita
Afeta: CLAUDE.md

### D-006 Merge Collection em espaço Original
Decisão: Collection Info em Original: a collection entra como está em volta da origem do mundo, sem rotação, e acompanha posição, rotação e escala do objeto com o modificador.
Por quê: o usuário quer exportar a collection como um objeto que ele posiciona.
Origem: usuário
Não escolhido: Relative - deixava a malha onde os objetos estão no mundo, ignorando o suporte.

### D-007 Spherical Bend vem do Loja.blend, com Dome Height
Decisão: os node groups vão em `assets/spherical_bend.blend`, tirados do grupo do Loja.blend; Flatten e Crown viraram Dome Height (scale Z só da parte curva, arco virando elipse com a casca pela normal); Limit Radius começa em 700.
Por quê: o Flatten fazia um arco de dois raios, não o achatamento que o usuário quer.
Origem: usuário (Dome Height, 700); topo fixo no achatamento: escolha da IA, ainda sem resposta do usuário

### D-008 Arabesque: gaiola aberta só de quads, um anel por vértice
Decisão: cada vértice do esqueleto vira um anel do perfil (5 pontos, crista com Crest); sem suavização, sem tampas, sem face de trás, sem Boolean, sem crease nem bevel; Subdivision fica fora, por conta do usuário.
Por quê: o usuário põe o Subdivision antes ou depois; triângulos e malha fechada quebravam o Subdivision.
Origem: usuário
Não escolhido: Catmull-Rom reamostrado - parecia subdivisão; Mesh Boolean Union - triângulos e malha fechada.

### D-009 Arabesque: grupos por nome digitado e solda nas junções
Decisão: Stem Group e Width Group são inputs de texto com o nome do vertex group. O segmento principal (arestas entre vértices do Stem Group) é uma spline contínua; em toda junção os anéis das extensões são soldados num anel âncora (o do segmento principal, ou o da extensão de menor índice), achado por Sample Nearest num "espaço de chave".
Por quê: o ícone de atributo confundiu o usuário (grupo foi parar no input errado); a malha precisa sair inteira.
Origem: usuário (segmento marcado, conectar); texto e âncora: sugestão da IA aceita
Afeta: arabesque.py (`build_weld`)

### D-010 Arabesque: Grupo de Largura sobrescreve a largura
Decisão: peso acima de 0 dá largura = peso × Max Group Width; peso 0 (ou fora do grupo) usa Width. Abaixo de Width a altura cai junto (peso mínimo vira ponto); acima, fica em Thickness. Painéis: Main Stem (Stem Group, Width, Thickness, Crest) e Connected Branches (Connect to Stem, Width Group, Max Group Width).
Por quê: o usuário quer controlar a largura pintando pesos, como weight paint de bones.
Origem: usuário
Não escolhido: afinamento automático das pontas e folhas por ângulo - removidos pelo usuário.

## Fatos verificados

### F-001 Inputs de modificador Geometry Nodes no Blender 5.2
Fato: `modifier[identifier]` não funciona mais; usar `modifier.properties.inputs.<identifier>`, com `.value`, `.type` ('VALUE', 'ATTRIBUTE', 'LAYER') e `.attribute_name`. Input novo de um grupo reconstruído pode ficar com 0 em vez do padrão até ser definido.
Fonte: teste no Blender 5.2.2
Verificado: 2026-10-25

### F-002 Modificadores não guardam propriedades Python
Fato: `bpy.types.MirrorModifier.x = BoolProperty(...)` não registra nada (nem com get/set). Subpainel Python com `bl_parent_id = "MOD_PT_Mirror"` funciona e recebe o modificador em `self.custom_data`; ler `custom_data` no primeiro desenho de um subpainel criado depois do painel derruba o Blender, por isso o primeiro desenho é pulado.
Fonte: teste no Blender 5.2.2 e crash log (`Panel_custom_data_get`)
Verificado: 2026-10-25

### F-003 Separate Transform falha em objeto espelhado
Fato: para matriz com escala negativa, Separate Transform devolve escala 1; o tamanho de cada eixo sai certo com Transform Direction + Length.
Fonte: teste no Blender 5.2.2
Verificado: 2026-10-25
Afeta: D-008

### F-004 Peso 0 e fora do grupo são iguais no Geometry Nodes
Fato: Named Attribute de um vertex group devolve 0 para vértices fora dele; não há como diferenciar de peso 0.
Fonte: teste no Blender 5.2.2
Verificado: 2026-10-25
Afeta: D-010

### F-005 Nós que mudaram no Blender 5.2
Fato: Set Curve Normal, Resample Curve e Transform Geometry têm "Mode" como socket de menu (`'Z Up'`, `'Length'`); o trapézio do Quadrilateral tem Offset padrão de 1 m; Curve to Mesh tem input Scale, e ligado nele o raio da curva é ignorado.
Fonte: teste no Blender 5.2.2
Verificado: 2026-10-25

### F-006 Curve to Mesh com normal Z Up
Fato: o X do perfil fica no plano e o Y na direção da normal, mas o lado do plano e o sentido das faces variam com a direção de cada spline.
Fonte: teste no Blender 5.2.2
Verificado: 2026-10-25
Afeta: D-008
