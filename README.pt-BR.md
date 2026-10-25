**Português** · [English](README.md) (em desenvolvimento)

# Fofuxo Modeling Tools

Add-on para o Blender com ferramentas que agilizam a modelagem e a exportação:

- um checkbox **Angle** dentro do modificador Mirror, que faz ele espelhar num
  plano inclinado a 45°, e não só nos planos X/Y/Z a 90° um do outro;
- o modificador **Merge Collection**, que junta todos os objetos de uma
  collection numa malha só, pronta para exportar;
- o modificador **Spherical Bend**, que curva uma malha plana numa abóbada,
  com pilares e decoração opcionais.

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

Os modificadores novos ficam no submenu *Add Modifier > Fofuxo*.

O **Merge Collection** é um modificador Geometry Nodes: escolha a collection no painel e a malha do objeto passa a
conter cópias de todos os objetos dela (inclusive sub-collections, curvas e
textos), já com os modificadores e materiais deles, na mesma posição em que
estão na cena. Para exportar, use uma malha vazia como suporte e esconda ou
exclua a collection de origem.

- O suporte precisa ser um objeto mesh: empties não aceitam modificadores.
- O suporte não pode estar dentro da collection que ele junta. Isso cria um
  ciclo de dependência e o resultado fica vazio.

O **Spherical Bend** também é Geometry Nodes. O **Dome Height** muda só a
altura da parte curva, como um scale Z nela: 1 deixa a abóbada redonda, abaixo
de 1 achata o topo. O topo fica onde está e a parte reta acompanha o fim do
arco; com *Use Floor* ligado, ela continua indo até o piso.

Os dois modificadores Geometry Nodes ficam salvos no `.blend`, então quem abre
o arquivo sem o add-on vê o mesmo resultado.

## Licença

[GPL-3.0-or-later](LICENSE), a mesma licença do Blender.
