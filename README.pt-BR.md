**Português** · [English](README.md) (em desenvolvimento)

# Fofuxo Modeling Tools

Add-on para o Blender com ferramentas que agilizam a modelagem. A primeira é um
checkbox **Angle** dentro do modificador Mirror, que faz ele espelhar num plano
inclinado a 45°, e não só nos planos X/Y/Z a 90° um do outro.

- [Instalação](#instalação)
- [Uso](#uso)
- [Licença](#licença)

## Instalação

Requer Blender 4.2 ou mais novo.

1. Baixe o `.zip` da página de [Releases](https://github.com/uayten/FofuxoModelingTools/releases).
2. No Blender, arraste o `.zip` para dentro da janela, ou vá em
   *Edit > Preferences > Get Extensions*, abra o menu ⌄ no canto superior
   direito e escolha *Install from Disk*.

Para gerar o `.zip` a partir do código:

```bash
blender --command extension build --source-dir fofuxo_modeling_tools
```

## Uso

O checkbox **Angle** fica no fim do painel do modificador Mirror. Ao marcar,
ele cria um empty oculto, filho do objeto, e o põe como *Mirror Object*: é esse
empty que define o plano do espelho. A rotação dele aparece dentro do
subpainel e pode ser mudada para outro ângulo. Desmarcar apaga o empty.

## Licença

[GPL-3.0-or-later](LICENSE), a mesma licença do Blender.
