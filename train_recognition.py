"""
LEGACY:
    View more, visit my tutorial page: https://morvanzhou.github.io/tutorials/
    My Youtube Channel: https://www.youtube.com/user/MorvanZhou
    Dependencies:
    torch: 0.4
    matplotlib
    numpy
"""
import os
import io
import torch
import torchvision
import numpy             as np
import torch.nn          as nn
import torch.optim       as optim
import torch.utils.data  as Data

#import models.models_import as models_import
#model = models_import.create_model_object(model_name='resnet101', num_classes=21, sample_size=224, sample_duration=16)
#import pdb; pdb.set_trace()
#from utils                     import save_checkpoint, load_checkpoint, accuracy, accuracy_action
from parse_args                import Parse
from checkpoint                import save_checkpoint, load_checkpoint
#from torchvision               import datasets, transforms
from datasets                  import data_loader
from tensorboardX              import SummaryWriter
from torch.autograd            import Variable
from torch.optim.lr_scheduler  import MultiStepLR

# Import models 
from models.models_import      import create_model_object

def train(**args):

    print("Experimental Setup: ", args)

    avg_acc = []

    for total_iteration in range(args['rerun']):

        # Tensorboard Element
        writer = SummaryWriter()

        # Load Data
        loader = data_loader(**args)

        if args['load_type'] == 'train':
            trainloader = loader['train']

        elif args['load_type'] == 'train_val':
            trainloader = loader['train']
            testloader  = loader['valid'] 

        else:
            print('Invalid environment selection for training, exiting')

        # END IF
    
        # Check if GPU is available (CUDA)
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
        # Load Network # EDIT
        model = create_model_object(model_name=args['model'],num_classes=args['labels'], sample_size=args['sample_size'], sample_duration=args['sample_duration']).to(device)

        # Training Setup
        params     = [p for p in model.parameters() if p.requires_grad]

        if args['opt'] == 'sgd':
            optimizer  = optim.SGD(params, lr=args['lr'], momentum=args['momentum'], weight_decay=args['weight_decay'])

        elif args['opt'] == 'adam':
            optimizer  = optim.Adam(params, lr=args['lr'], weight_decay=args['weight_decay'])
        
        else:
            print('Unsupported optimizer selected. Exiting')
            exit(1)

        # END IF
            
        scheduler  = MultiStepLR(optimizer, milestones=args['milestones'], gamma=args['gamma'])    

    ############################################################################################################################################################################

        # Start: Training Loop
        for epoch in range(args['epoch']):
            running_loss = 0.0
            print('Epoch: ', epoch)

            # Setup Model To Train 
            model.train()

            # Start: Epoch
            for step, data in enumerate(trainloader):
    
                # (True Batch, Augmented Batch, Sequence Length)
                x_input       = data['data'].to(device) 
                y_label       = data['labels'].to(device) 

                optimizer.zero_grad()

                outputs = model(x_input)

                # EDIT
                loss    = torch.mean(torch.sum(-y_label * nn.functional.log_softmax(outputs,dim=1), dim=1))
    
                loss.backward()
                optimizer.step()
    
                running_loss += loss.item()

                # Add Loss Element
                writer.add_scalar(args['dataset']+'/'+args['model']+'/loss', loss.item(), epoch*len(trainloader) + step)

                if np.isnan(running_loss):
                    import pdb; pdb.set_trace()
   
                if step % 100 == 0:
                    #print('Epoch: ', epoch, '| train loss: %.4f' % (running_loss/100.))
                    print('Epoch: {}/{}, step: {}/{} | train loss: {:.4f}'.format(epoch, args['epoch'], step, len(trainloader), running_loss/100.))
                    running_loss = 0.0

                # END IF

            # Save Current Model
            save_path = os.path.join(args['save_dir'],args['model'])

            if not os.path.isdir(args['save_dir']):
                os.mkdir(args['save_dir'])
            if not os.path.isdir(save_path):
                os.mkdir(save_path)

            save_checkpoint(epoch, 0, model, optimizer, os.path.join(save_path,args['dataset']+'_epoch'+str(epoch)+'.pkl'))
   
            # END FOR: Epoch

            scheduler.step()

            acc = 100*accuracy_action(model, testloader, device)
            writer.add_scalar(args['dataset']+'/'+args['model']+'/train_accuracy', acc, epoch)
 
            print('Accuracy of the network on the training set: %d %%\n' % (acc))
    
        # END FOR: Training Loop

    ############################################################################################################################################################################

        # Close Tensorboard Element
        writer.close()

        # Save Final Model
        save_checkpoint(epoch + 1, 0, model, optimizer, args['save_dir']+'/'+str(total_iteration)+'/final_model.pkl')
        avg_acc.append(100.*accuracy(model, testloader, device))
    
    print("Average training accuracy across %d runs is %f" %(args['rerun'], np.mean(avg_acc)))



if __name__ == "__main__":

    parse = Parse()
    args = parse.get_args()

    # For reproducibility
    torch.backends.cudnn.deterministic = True
    torch.manual_seed(args['seed'])
    np.random.seed(args['seed'])

    train(**args)
