import time
import math
import torch 
import torch.nn as nn
from torch import optim
import torchvision
from a5_helper import *
import matplotlib.pyplot as plt


def hello_single_stage_detector():
    print("Hello from single_stage_detector.py!")


def GenerateAnchor(anc, grid):
  """
  Anchor generator.

  Inputs:
  - anc: Tensor of shape (A, 2) giving the shapes of anchor boxes to consider at
    each point in the grid. anc[a] = (w, h) gives the width and height of the
    a'th anchor shape.
  - grid: Tensor of shape (B, H', W', 2) giving the (x, y) coordinates of the
    center of each feature from the backbone feature map. This is the tensor
    returned from GenerateGrid.
  
  Outputs:
  - anchors: Tensor of shape (B, A, H', W', 4) giving the positions of all
    anchor boxes for the entire image. anchors[b, a, h, w] is an anchor box
    centered at grid[b, h, w], whose shape is given by anc[a]; we parameterize
    boxes as anchors[b, a, h, w] = (x_tl, y_tl, x_br, y_br), where (x_tl, y_tl)
    and (x_br, y_br) give the xy coordinates of the top-left and bottom-right
    corners of the box.
  """
  anchors = None
  ##############################################################################
  # TODO: Given a set of anchor shapes and a grid cell on the activation map,  #
  # generate all the anchor coordinates for each image. Support batch input.   #
  ##############################################################################
  # Replace "pass" statement with your code
  B, H, W, _ = grid.shape
  A, _ = anc.shape
  
  grid = grid.view(B, 1, H, W, -1)
  anc = anc.view(1, A, 1, 1, -1)
  
  half_w = anc[..., 0] / 2
  half_h = anc[..., 1] / 2
  
  x_tl = grid[..., 0] - half_w
  y_tl = grid[..., 1] - half_h
  x_br = grid[..., 0] + half_w
  y_br = grid[..., 1] + half_h
  
  anchors = torch.stack([x_tl, y_tl, x_br, y_br], dim=-1)
  ##############################################################################
  #                               END OF YOUR CODE                             #
  ##############################################################################

  return anchors


def GenerateProposal(anchors, offsets, method='YOLO'):
  """
  Proposal generator.

  Inputs:
  - anchors: Anchor boxes, of shape (B, A, H', W', 4). Anchors are represented
    by the coordinates of their top-left and bottom-right corners.
  - offsets: Transformations of shape (B, A, H', W', 4) that will be used to
    convert anchor boxes into region proposals. The transformation
    offsets[b, a, h, w] = (tx, ty, tw, th) will be applied to the anchor
    anchors[b, a, h, w]. For YOLO, assume that tx and ty are in the range
    (-0.5, 0.5).
  - method: Which transformation formula to use, either 'YOLO' or 'FasterRCNN'
  
  Outputs:
  - proposals: Region proposals of shape (B, A, H', W', 4), represented by the
    coordinates of their top-left and bottom-right corners. Applying the
    transform offsets[b, a, h, w] to the anchor [b, a, h, w] should give the
    proposal proposals[b, a, h, w].
  
  """
  assert(method in ['YOLO', 'FasterRCNN'])
  proposals = None
  ##############################################################################
  # TODO: Given anchor coordinates and the proposed offset for each anchor,    #
  # compute the proposal coordinates using the transformation formulas above.  #
  ##############################################################################
  # Replace "pass" statement with your code
  x_tl, y_tl, x_br, y_br = anchors.unbind(dim=-1)
  tx, ty, tw, th = offsets.unbind(dim=-1)
  
  xa, ya, wa, ha = (x_br + x_tl) / 2, (y_br + y_tl) / 2, x_br - x_tl, y_br - y_tl
  
  if method == 'YOLO':
      xp = xa + tx
      yp = ya + ty
      wp = wa * torch.exp(tw)
      hp = ha * torch.exp(th)
  else:
      xp = xa + tx * wa
      yp = ya + tx * ha
      wp = wa * torch.exp(tw)
      hp = ha * torch.exp(th)
  
  proposals = torch.stack([xp - wp/2, yp - hp/2, xp + wp/2, yp + hp/2], dim=-1)
  ##############################################################################
  #                               END OF YOUR CODE                             #
  ##############################################################################

  return proposals


def IoU(proposals, bboxes):
  """
  Compute intersection over union between sets of bounding boxes.

  Inputs:
  - proposals: Proposals of shape (B, A, H', W', 4)
  - bboxes: Ground-truth boxes from the DataLoader of shape (B, N, 5).
    Each ground-truth box is represented as tuple (x_lr, y_lr, x_rb, y_rb, class).
    If image i has fewer than N boxes, then bboxes[i] will be padded with extra
    rows of -1.
  
  Outputs:
  - iou_mat: IoU matrix of shape (B, A*H'*W', N) where iou_mat[b, i, n] gives
    the IoU between one element of proposals[b] and bboxes[b, n].

  For this implementation you DO NOT need to filter invalid proposals or boxes;
  in particular you don't need any special handling for bboxxes that are padded
  with -1.
  """
  iou_mat = None
  ##############################################################################
  # TODO: Compute the Intersection over Union (IoU) on proposals and GT boxes. #
  # No need to filter invalid proposals/bboxes (i.e., allow region area <= 0). #
  # However, you need to make sure to compute the IoU correctly (it should be  #
  # 0 in those cases.                                                          # 
  # You need to ensure your implementation is efficient (no for loops).        #
  # HINT:                                                                      #
  # IoU = Area of Intersection / Area of Union, where                          #
  # Area of Union = Area of Proposal + Area of BBox - Area of Intersection     #
  # and the Area of Intersection can be computed using the top-left corner and #
  # bottom-right corner of proposal and bbox. Think about their relationships. #
  ##############################################################################
  # Replace "pass" statement with your code
  B, A, H, W, _ = proposals.shape
  
  x_tl_prop, y_tl_prop, x_br_prop, y_br_prop = proposals.view(B, A*H*W, -1).unsqueeze(2).unbind(dim=-1)
  x_tl_bbox, y_tl_bbox, x_br_bbox, y_br_bbox, _ = bboxes.unsqueeze(1).unbind(dim=-1)
  
  x_tl_inter = torch.maximum(x_tl_prop, x_tl_bbox)
  y_tl_inter = torch.maximum(y_tl_prop, y_tl_bbox)
  x_br_inter = torch.minimum(x_br_prop, x_br_bbox)
  y_br_inter = torch.minimum(y_br_prop, y_br_bbox)
  
  area_w = torch.maximum(torch.zeros_like(x_tl_inter), x_br_inter - x_tl_inter)
  area_h = torch.maximum(torch.zeros_like(y_tl_inter), y_br_inter - y_tl_inter)
  area_inter = area_w * area_h
  
  area_prop = (x_br_prop - x_tl_prop) * (y_br_prop - y_tl_prop)
  area_bbox = (x_br_bbox - x_tl_bbox) * (y_br_bbox - y_tl_bbox)
  
  area_union = area_prop + area_bbox - area_inter
  
  iou = area_inter / area_union
  iou_mat = iou.view(B, A*H*W, -1)
  ##############################################################################
  #                               END OF YOUR CODE                             #
  ##############################################################################
  return iou_mat


class PredictionNetwork(nn.Module):
  def __init__(self, in_dim, hidden_dim=128, num_anchors=9, num_classes=20, drop_ratio=0.3):
    super().__init__()

    assert(num_classes != 0 and num_anchors != 0)
    self.num_classes = num_classes
    self.num_anchors = num_anchors

    ##############################################################################
    # TODO: Set up a network that will predict outputs for all anchors. This     #
    # network should have a 1x1 convolution with hidden_dim filters, followed    #
    # by a Dropout layer with p=drop_ratio, a Leaky ReLU nonlinearity, and       #
    # finally another 1x1 convolution layer to predict all outputs. You can      #
    # use an nn.Sequential for this network, and store it in a member variable.  #
    # HINT: The output should be of shape (B, 5*A+C, 7, 7), where                #
    # A=self.num_anchors and C=self.num_classes.                                 #
    ##############################################################################
    # Make sure to name your prediction network pred_layer.
    self.pred_layer = None
    # Replace "pass" statement with your code
    A, C = num_anchors, num_classes
    self.net = nn.Sequential(
        nn.Conv2d(in_dim, hidden_dim, 1),
        nn.Dropout2d(p=drop_ratio),
        nn.LeakyReLU(),
        nn.Conv2d(hidden_dim, 5*A+C, 1)
    )
    ##############################################################################
    #                               END OF YOUR CODE                             #
    ##############################################################################

  def _extract_anchor_data(self, anchor_data, anchor_idx):
    """
    Inputs:
    - anchor_data: Tensor of shape (B, A, D, H, W) giving a vector of length
      D for each of A anchors at each point in an H x W grid.
    - anchor_idx: int64 Tensor of shape (M,) giving anchor indices to extract

    Returns:
    - extracted_anchors: Tensor of shape (M, D) giving anchor data for each
      of the anchors specified by anchor_idx.
    """
    B, A, D, H, W = anchor_data.shape
    anchor_data = anchor_data.permute(0, 1, 3, 4, 2).contiguous().view(-1, D)
    extracted_anchors = anchor_data[anchor_idx]
    return extracted_anchors
  
  def _extract_class_scores(self, all_scores, anchor_idx):
    """
    Inputs:
    - all_scores: Tensor of shape (B, C, H, W) giving classification scores for
      C classes at each point in an H x W grid.
    - anchor_idx: int64 Tensor of shape (M,) giving the indices of anchors at
      which to extract classification scores

    Returns:
    - extracted_scores: Tensor of shape (M, C) giving the classification scores
      for each of the anchors specified by anchor_idx.
    """
    B, C, H, W = all_scores.shape
    A = self.num_anchors
    all_scores = all_scores.contiguous().permute(0, 2, 3, 1).contiguous()
    all_scores = all_scores.view(B, 1, H, W, C).expand(B, A, H, W, C)
    all_scores = all_scores.reshape(B * A * H * W, C)
    extracted_scores = all_scores[anchor_idx]
    return extracted_scores

  def forward(self, features, pos_anchor_idx=None, neg_anchor_idx=None):
    """
    Run the forward pass of the network to predict outputs given features
    from the backbone network.

    Inputs:
    - features: Tensor of shape (B, in_dim, 7, 7) giving image features computed
      by the backbone network.
    - pos_anchor_idx: int64 Tensor of shape (M,) giving the indices of anchors
      marked as positive. These are only given during training; at test-time
      this should be None.
    - neg_anchor_idx: int64 Tensor of shape (M,) giving the indices of anchors
      marked as negative. These are only given at training; at test-time this
      should be None.
    
    The outputs from this method are different during training and inference.
    
    During training, pos_anchor_idx and neg_anchor_idx are given and identify
    which anchors should be positive and negative, and this forward pass needs
    to extract only the predictions for the positive and negative anchors.

    During inference, only features are provided and this method needs to return
    predictions for all anchors.

    Outputs (During training):
    - conf_scores: Tensor of shape (2*M, 1) giving the predicted classification
      scores for positive anchors and negative anchors (in that order).
    - offsets: Tensor of shape (M, 4) giving predicted transformation for
      positive anchors.
    - class_scores: Tensor of shape (M, C) giving classification scores for
      positive anchors.

    Outputs (During inference):
    - conf_scores: Tensor of shape (B, A, H, W) giving predicted classification
      scores for all anchors.
    - offsets: Tensor of shape (B, A, 4, H, W) giving predicted transformations
      all all anchors.
    - class_scores: Tensor of shape (B, C, H, W) giving classification scores for
      each spatial position.
    """
    conf_scores, offsets, class_scores = None, None, None
    ############################################################################
    # TODO: Use backbone features to predict conf_scores, offsets, and         #
    # class_scores. Make sure conf_scores is between 0 and 1 by squashing the  #
    # network output with a sigmoid. Also make sure the first two elements t^x #
    # and t^y of offsets are between -0.5 and 0.5 by squashing with a sigmoid  #
    # and subtracting 0.5.                                                     #
    #                                                                          #
    # During training you need to extract the outputs for only the positive    #
    # and negative anchors as specified above.                                 #
    #                                                                          #
    # HINT: You can use the provided helper methods self._extract_anchor_data  #
    # and self._extract_class_scores to extract information for positive and   #
    # negative anchors specified by pos_anchor_idx and neg_anchor_idx.         #
    ############################################################################
    # Replace "pass" statement with your code
    A, C = self.num_anchors, self.num_classes
    B, _, H, W = features.shape
    out = self.net(features)
    class_scores = out[:, 5*A:, :, :]
    
    anchors = out[:, :5*A, :, :].view(B, A, 5, H, W)
    offsets = torch.cat((torch.sigmoid(anchors[:, :, 1:3, :, :]) - 0.5, anchors[:, :, 3:, :, :]), dim=2)
    conf_scores = torch.sigmoid(anchors[:, :, [0], :, :])
    
    if pos_anchor_idx is not None:
        offsets = self._extract_anchor_data(offsets, pos_anchor_idx)
        class_scores = self._extract_class_scores(class_scores, pos_anchor_idx)
        pos = self._extract_anchor_data(conf_scores, pos_anchor_idx)
        neg = self._extract_anchor_data(conf_scores, neg_anchor_idx)
        conf_scores = torch.cat((pos, neg), dim=0)
    else:
        conf_scores = conf_scores.squeeze()
    ##############################################################################
    #                               END OF YOUR CODE                             #
    ##############################################################################
    return conf_scores, offsets, class_scores


class SingleStageDetector(nn.Module):
  def __init__(self):
    super().__init__()

    self.anchor_list = torch.tensor([[1., 1], [2, 2], [3, 3], [4, 4], [5, 5], [2, 3], [3, 2], [3, 5], [5, 3]]) # READ ONLY
    self.feat_extractor = FeatureExtractor()
    self.num_classes = 20
    self.pred_network = PredictionNetwork(1280, num_anchors=self.anchor_list.shape[0], \
                                          num_classes=self.num_classes)
  def forward(self, images, bboxes):
    """
    Training-time forward pass for the single-stage detector.

    Inputs:
    - images: Input images, of shape (B, 3, 224, 224)
    - bboxes: GT bounding boxes of shape (B, N, 5) (padded)

    Outputs:
    - total_loss: Torch scalar giving the total loss for the batch.
    """
    # weights to multiple to each loss term
    w_conf = 1 # for conf_scores
    w_reg = 1 # for offsets
    w_cls = 1 # for class_prob

    total_loss = None
    ##############################################################################
    # TODO: Implement the forward pass of SingleStageDetector.                   #
    # A few key steps are outlined as follows:                                   #
    # i) Image feature extraction,                                               #
    # ii) Grid and anchor generation,                                            #
    # iii) Compute IoU between anchors and GT boxes and then determine activated/#
    #      negative anchors, and GT_conf_scores, GT_offsets, GT_class,           #
    # iv) Compute conf_scores, offsets, class_prob through the prediction network#
    # v) Compute the total_loss which is formulated as:                          #
    #    total_loss = w_conf * conf_loss + w_reg * reg_loss + w_cls * cls_loss,  #
    #    where conf_loss is determined by ConfScoreRegression, w_reg by          #
    #    BboxRegression, and w_cls by ObjectClassification.                      #
    # HINT: Set `neg_thresh=0.2` in ReferenceOnActivatedAnchors in this notebook #
    #       (A5-1) for a better performance than with the default value.         #
    ##############################################################################
    # Replace "pass" statement with your code
    B, N, _ = bboxes.shape
    A = len(self.anchor_list)
    
    # i) Image feature extraction
    img_features = self.feat_extractor(images)
    
    # ii) Grid and anchor generation
    grid = GenerateGrid(B)
    anchors = GenerateAnchor(self.anchor_list.to(grid.device), grid)
    
    # iii) Compute IoU between anchors and GT boxes
    ious = IoU(anchors, bboxes)
    # Determine activated/negative anchors, GT_conf_scores, GT_offsets, GT_class
    activated_anc_ind, negative_anc_ind, GT_conf_scores, \
    GT_offsets, GT_class, activated_anc_coord, negative_anc_coord = \
        ReferenceOnActivatedAnchors(anchors, bboxes, grid, ious, neg_thresh=0.2, method='YOLO')
    
    # iv) Compute conf_scores, offsets, class_prob through the prediction network
    conf_scores, offsets, class_scores = self.pred_network(img_features, activated_anc_ind, negative_anc_ind)
    
    # v) Compute the total_loss
    conf_loss = ConfScoreRegression(conf_scores, GT_conf_scores)
    reg_loss = BboxRegression(offsets, GT_offsets)
    anc_per_img = torch.prod(torch.tensor(anchors.shape[1:-1]))
    cls_loss = ObjectClassification(class_scores, GT_class, B, anc_per_img, activated_anc_ind)
    
    total_loss = w_conf * conf_loss + w_reg * reg_loss + w_cls * cls_loss
    ##############################################################################
    #                               END OF YOUR CODE                             #
    ##############################################################################

    return total_loss
  
  def inference(self, images, thresh=0.5, nms_thresh=0.7):
    """"
    Inference-time forward pass for the single stage detector.

    Inputs:
    - images: Input images
    - thresh: Threshold value on confidence scores
    - nms_thresh: Threshold value on NMS

    Outputs:
    - final_propsals: Keeped proposals after confidence score thresholding and NMS,
                      a list of B (*x4) tensors
    - final_conf_scores: Corresponding confidence scores, a list of B (*x1) tensors
    - final_class: Corresponding class predictions, a list of B  (*x1) tensors
    """
    final_proposals, final_conf_scores, final_class = [], [], []
    ##############################################################################
    # TODO: Predicting the final proposal coordinates `final_proposals`,         #
    # confidence scores `final_conf_scores`, and the class index `final_class`.  #
    # The overall steps are similar to the forward pass but now you do not need  #
    # to decide the activated nor negative anchors.                              #
    # HINT: Thresholding the conf_scores based on the threshold value `thresh`.  #
    # Then, apply NMS (torchvision.ops.nms) to the filtered proposals given the  #
    # threshold `nms_thresh`.                                                    #
    # The class index is determined by the class with the maximal probability.   #
    # Note that `final_propsals`, `final_conf_scores`, and `final_class` are all #
    # lists of B 2-D tensors (you may need to unsqueeze dim=1 for the last two). #
    ##############################################################################
    # Replace "pass" statement with your code
    # i) Image feature extraction
    with torch.no_grad():
      img_features = self.feat_extractor(images)
      B, _, H, W = img_features.shape
      A = len(self.anchor_list)
      
      # ii) Grid and anchor generation
      grid = GenerateGrid(B)
      anchors = GenerateAnchor(self.anchor_list.to(grid.device), grid)
      
      # iii) Compute conf_scores, offsets, class_prob through the prediction network
      conf_scores, offsets, class_scores = self.pred_network(img_features)
      C = class_scores.shape[1]
      
      # iv) Generate proposal
      offsets = offsets.permute(0, 1, 3, 4, 2).contiguous()
      proposals = GenerateProposal(anchors, offsets)
      
      # v) Post-process predictions
      for b in range(B):
          # get mask based on thresh
          conf_scores_mask = conf_scores[b] > thresh
          
          # get boxes for nms
          boxes = proposals[b][conf_scores_mask].view(-1, 4)
          # get scores for nms
          scores = conf_scores[b][conf_scores_mask].view(-1)
          # get elements keeped from nms
          nms_indices = torchvision.ops.nms(boxes, scores, nms_thresh)
          
          # get class index for final_class
          clsco = class_scores[b].permute(1, 2, 0).unsqueeze(0).expand(A, H, W, C)
          clsco = torch.argmax(clsco, dim=3)[conf_scores_mask].view(-1)
          
          final_proposals.append(boxes[nms_indices])
          final_conf_scores.append(scores[nms_indices].unsqueeze(1))
          final_class.append(clsco[nms_indices].unsqueeze(1))
    ##############################################################################
    #                               END OF YOUR CODE                             #
    ##############################################################################
    return final_proposals, final_conf_scores, final_class


def nms(boxes, scores, iou_threshold=0.5, topk=None):
  """
  Non-maximum suppression removes overlapping bounding boxes.

  Inputs:
  - boxes: top-left and bottom-right coordinate values of the bounding boxes
    to perform NMS on, of shape Nx4
  - scores: scores for each one of the boxes, of shape N
  - iou_threshold: discards all overlapping boxes with IoU > iou_threshold; float
  - topk: If this is not None, then return only the topk highest-scoring boxes.
    Otherwise if this is None, then return all boxes that pass NMS.

  Outputs:
  - keep: torch.long tensor with the indices of the elements that have been
    kept by NMS, sorted in decreasing order of scores; of shape [num_kept_boxes]
  """

  if (not boxes.numel()) or (not scores.numel()):
    return torch.zeros(0, dtype=torch.long)

  keep = None
  #############################################################################
  # TODO: Implement non-maximum suppression which iterates the following:     #
  #       1. Select the highest-scoring box among the remaining ones,         #
  #          which has not been chosen in this step before                    #
  #       2. Eliminate boxes with IoU > threshold                             #
  #       3. If any boxes remain, GOTO 1                                      #
  #       Your implementation should not depend on a specific device type;    #
  #       you can use the device of the input if necessary.                   #
  # HINT: You can refer to the torchvision library code:                      #
  #   github.com/pytorch/vision/blob/master/torchvision/csrc/cpu/nms_cpu.cpp  #
  #############################################################################
  # Replace "pass" statement with your code
  sorted_indices = torch.argsort(scores, descending=True)
  boxes = boxes[sorted_indices]
  scores = scores[sorted_indices]
  keep = []
  
  def calculate_iou(box1, box2):
      x_tl, y_tl = torch.max(box1[0], box2[:, 0]), torch.max(box1[1], box2[:, 1])
      x_br, y_br = torch.min(box1[2], box2[:, 2]), torch.min(box1[3], box2[:, 3])
      w = torch.max(torch.tensor(0.0), x_br - x_tl)
      h = torch.max(torch.tensor(0.0), y_br - y_tl)
      inter = w * h
      area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
      area2 = (box2[:, 2] - box2[:, 0]) * (box2[:, 3] - box2[:, 1])
      union = area1 + area2 - inter
      return inter / union
  
  while boxes.numel():
      box = boxes[0]
      keep.append(sorted_indices[0])
      
      iou = calculate_iou(box, boxes[1:])
      
      mask = iou < iou_threshold
      boxes = boxes[1:][mask]
      scores = scores[1:][mask]
      sorted_indices = sorted_indices[1:][mask]
      
      if topk is not None and len(keep) >= topk:
          break
  
  keep = torch.tensor(keep, dtype=torch.long)
  #############################################################################
  #                              END OF YOUR CODE                             #
  #############################################################################
  return keep

def ConfScoreRegression(conf_scores, GT_conf_scores):
  """
  Use sum-squared error as in YOLO

  Inputs:
  - conf_scores: Predicted confidence scores
  - GT_conf_scores: GT confidence scores
  
  Outputs:
  - conf_score_loss
  """
  # the target conf_scores for negative samples are zeros
  GT_conf_scores = torch.cat((torch.ones_like(GT_conf_scores), \
                              torch.zeros_like(GT_conf_scores)), dim=0).view(-1, 1)
  conf_score_loss = torch.sum((conf_scores - GT_conf_scores)**2) * 1. / GT_conf_scores.shape[0]
  return conf_score_loss


def BboxRegression(offsets, GT_offsets):
  """"
  Use sum-squared error as in YOLO
  For both xy and wh

  Inputs:
  - offsets: Predicted box offsets
  - GT_offsets: GT box offsets
  
  Outputs:
  - bbox_reg_loss
  """
  bbox_reg_loss = torch.sum((offsets - GT_offsets)**2) * 1. / GT_offsets.shape[0]
  return bbox_reg_loss

