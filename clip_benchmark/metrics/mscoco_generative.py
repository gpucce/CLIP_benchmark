import json
from pycocoevalcap.eval import COCOEvalCap
from open_clip import tokenize
from tqdm.auto import tqdm
from open_clip.tokenizer import _tokenizer
import torch

def evaluate(model, dataloader, batch_size, device, transform, train_dataloader=None, num_workers=None, amp=True, verbose=False):
    coco = dataloader.dataset.coco
    indexer = dataloader.dataset.ids
    autocast = torch.cuda.amp.autocast if amp else suppress
    results = []
    for idx, (img, _) in enumerate(tqdm(dataloader)):
        n_samples = img.shape[0] # for last batch
        idxs = [indexer[idx * batch_size + id] for id in range(n_samples)]
        with torch.no_grad(), autocast():
            out = model.generate_beamsearch(img.to(device), 20, num_beams=6, num_beam_groups=3, sot_token_id=49406, eos_token_id=49407)
        decoded = [_tokenizer.decode(i).split("<end_of_text>")[0].replace("<start_of_text>", "").strip() for i in out.cpu().numpy()]
        for image_id, caption in zip(idxs, decoded):
            results.append({"image_id":image_id, "caption":caption})
    temp_res_file = "temp_results.json"
    with open(temp_res_file, "w") as jf:
        json.dump(results, jf)

    coco_result = coco.loadRes(temp_res_file)
    coco_eval = COCOEvalCap(coco, coco_result)
    coco_eval.evaluate()
    metrics = coco_eval.eval

    # print output evaluation scores
    for metric, score in metrics.items():
        print(f'{metric}: {score:.3f}')

    return metrics
