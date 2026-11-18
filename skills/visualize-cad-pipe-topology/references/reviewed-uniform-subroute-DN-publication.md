# 已回证统一水平管径的发布

源级同范围、独立前缀和下部成员均回证后，使用 `refresh-uniform-subroute-DN-viewer --parent OLD --output NEW --proof PROOF --templates T --port PORT`，再用 `validate-uniform-subroute-DN-viewer --verify-output NEW` 独立重放。源级规则见 [统一水平子路径](../../build-cad-pipe-topology/references/reviewed-uniform-subroute-DN.md)。

仅填此前未知的纯水平整边管径。混合边只增加有原生方向、源线和精确路径索引的水平子段管径；余下全部竖段仍取11图，不得填写混合边的整边管径。保留旧管径、全部长度、共享范围总量、元件及批注；内部节点对应和长度分摊仍未知。不同支路数不是一对一配对依据。

在实际查看器和两个完整网络的CSV核对生效：原291列除获准13条未知整边的管径三列外逐值保持，追加3列来源。15条边有水平子域来源，不能计作15条整边补齐。对照原图、技术验证、人工验收分别记账；历史完整入口未通过的发布阻断不得被局部成功关闭。
