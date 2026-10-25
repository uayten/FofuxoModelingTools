# Fofuxo Modeling Tools

Este projeto segue a convenção project-docs (ROADMAP.md, DECISIONS.md, HANDOFF.md).
Quando o usuário pedir para retomar ("retoma", "vamos continuar o projeto", "vamos continuar o desenvolvimento do roadmap"), antes de agir: ler HANDOFF.md; do ROADMAP.md, só os títulos (`grep "^### R-" ROADMAP.md`) e o item do próximo passo ou do pedido. Confirmar em 3 linhas o estado e o próximo passo e esperar o ok.

## Ambiente

- Blender 5.2.2 (Steam): `C:/Program Files (x86)/Steam/steamapps/common/Blender/blender`.
- Gerar o zip: `blender -b --factory-startup --command extension build --source-dir fofuxo_modeling_tools --output-dir .` e mandar o zip ao usuário.
- `graft/` é cache de uma ferramenta: ignorar.

## Testes

- Rodar o add-on sem instalar: `blender -b --factory-startup <arquivo> --python <script>`, com `sys.path.insert(0, <repo>)` e `import fofuxo_modeling_tools`; scripts de teste ficam na pasta temporária, não no repositório.
- Prints da interface: Blender sem `-b`, `bpy.app.timers` para mudar a aba e `bpy.ops.screen.screenshot`.
- Arquivo real do usuário: `C:\UnityProjects\MyDragonShop\Docs\Loja\Loja.blend` (objetos Arabescos Geometry Nodes e Nova Abóbada Geometry Nodes). Só leitura: nunca salvar por cima.
- O usuário mantém o Blender aberto: para parar um teste travado, matar só o processo do teste (pelo comando), nunca todos os `blender.exe`.
- Após `bpy.ops.wm.open_mainfile`, o objeto pode estar em Edit Mode: voltar para Object Mode antes de mexer.

## Código

- Mudou um node group gerado em código: subir `GROUP_VERSION` e, se renomeou input, pôr em `RENAMED_INPUTS` (D-005).
- Inputs de modificador no Blender 5.2: `modifier.properties.inputs` (F-001).
